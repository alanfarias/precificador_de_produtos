from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent
XML_DIR = BASE_DIR / "xml"
XML_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Gerador de Preço de Venda - NF-e")


def obter_namespace(root):
    for uri in ("http://www.portalfiscal.inf.br/nfe", "http://portalfiscal.inf.br"):
        ns = {"ns": uri}
        if root.find('.//ns:emit', ns) is not None:
            return ns
    return {"ns": "http://www.portalfiscal.inf.br/nfe"}


def processar_xml_conteudo(conteudo: bytes, pct_fixo: float, pct_simples: float, pct_cartao: float, pct_lucro: float):
    root = ET.fromstring(conteudo)
    ns = obter_namespace(root)

    emitente = root.find('.//ns:emit', ns)
    if emitente is None:
        raise HTTPException(status_code=400, detail="Estrutura de emitente inválida no XML.")

    fornecedor = {
        "cnpj": emitente.find('ns:CNPJ', ns).text if emitente.find('ns:CNPJ', ns) is not None else "CPF",
        "razao_social": emitente.find('ns:xNome', ns).text,
    }

    total_nota = root.find('.//ns:total/ns:ICMSTot', ns)
    if total_nota is None:
        raise HTTPException(status_code=400, detail="Estrutura de totais inválida no XML.")

    v_prod_total = float(total_nota.find('ns:vProd', ns).text or 0)
    v_frete_total = float(total_nota.find('ns:vFrete', ns).text or 0)
    v_seg_total = float(total_nota.find('ns:vSeg', ns).text or 0)
    v_outro_total = float(total_nota.find('ns:vOutro', ns).text or 0)
    despesas_globais_total = v_frete_total + v_seg_total + v_outro_total

    pct_variavel_total = pct_simples + pct_cartao
    soma_percentuais = (pct_fixo + pct_variavel_total + pct_lucro) / 100

    if soma_percentuais >= 1:
        raise HTTPException(status_code=400, detail="A soma das margens operacionais e lucro não pode atingir 100%.")

    produtos = []

    for det in root.findall('.//ns:det', ns):
        prod = det.find('ns:prod', ns)
        imposto = det.find('ns:imposto', ns)

        v_prod_item = float(prod.find('ns:vProd', ns).text)
        qtd = float(prod.find('ns:qCom', ns).text)

        codigo_ean = None
        ean_node = prod.find('ns:cEAN', ns)
        if ean_node is not None and ean_node.text:
            codigo_ean = ean_node.text
        else:
            ean_trib_node = prod.find('ns:cEANTrib', ns)
            if ean_trib_node is not None and ean_trib_node.text:
                codigo_ean = ean_trib_node.text
        if codigo_ean is None:
            codigo_ean = prod.find('ns:cProd', ns).text

        proporcao = v_prod_item / v_prod_total if v_prod_total > 0 else 0
        frete_rateado = despesas_globais_total * proporcao

        v_ipi = 0.0
        v_st = 0.0
        ipi_bloco = imposto.find('.//ns:IPI/ns:IPITrib', ns)
        if ipi_bloco is not None and ipi_bloco.find('ns:vIPI', ns) is not None:
            v_ipi = float(ipi_bloco.find('ns:vIPI', ns).text)
        st_bloco = imposto.find('.//ns:ICMS//ns:vICMSST', ns)
        if st_bloco is not None:
            v_st = float(st_bloco.text)

        custo_total_item = v_prod_item + v_ipi + v_st + frete_rateado
        custo_unitario_real = custo_total_item / qtd
        preco_venda_sugerido = custo_unitario_real / (1 - soma_percentuais)

        produtos.append(
            {
                "codigo": codigo_ean,
                "codigo_interno": prod.find('ns:cProd', ns).text,
                "descricao": prod.find('ns:xProd', ns).text,
                "custo_unitario_xml": float(prod.find('ns:vUnCom', ns).text),
                "custo_unitario_real": round(custo_unitario_real, 2),
                "preco_venda_sugerido": round(preco_venda_sugerido, 2),
            }
        )

    return {
        "fornecedor": fornecedor,
        "configuracoes_aplicadas": {
            "despesas_fixas_pct": pct_fixo,
            "simples_nacional_pct": pct_simples,
            "cartao_pct": pct_cartao,
            "lucro_desejado_pct": pct_lucro,
        },
        "produtos": produtos,
    }


# Permite que seu Frontend converse com o Backend sem problemas de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "index.html")


@app.post("/api/processar-xml")
async def processar_xml(
    file: Optional[UploadFile] = File(default=None),
    filename: Optional[str] = Form(default=None),
    pct_fixo: float = 15.0,
    pct_simples: float = 8.32,
    pct_cartao: float = 3.0,
    pct_lucro: float = 20.0,
):
    if file is None and not filename:
        raise HTTPException(
            status_code=400,
            detail="Envie um XML em multipart/form-data ou informe o nome do arquivo na pasta xml/ do servidor.",
        )

    try:
        if file is not None:
            if not file.filename or not file.filename.lower().endswith(".xml"):
                raise HTTPException(status_code=400, detail="O arquivo enviado deve ser um XML.")
            conteudo = await file.read()
        else:
            if not filename.lower().endswith(".xml"):
                raise HTTPException(status_code=400, detail="O nome do arquivo informado deve terminar em .xml.")
            caminho = (XML_DIR / filename).resolve()
            if XML_DIR not in caminho.parents and caminho != XML_DIR:
                raise HTTPException(status_code=400, detail="Arquivo fora do diretório permitido.")
            if not caminho.is_file():
                raise HTTPException(status_code=404, detail=f"Arquivo XML não encontrado na pasta xml/: {filename}")
            conteudo = caminho.read_bytes()

        return processar_xml_conteudo(conteudo, pct_fixo, pct_simples, pct_cartao, pct_lucro)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o XML: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
