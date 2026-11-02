from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import xml.etree.ElementTree as ET

app = FastAPI(title="Gerador de Preço de Venda - NF-e")


def obter_namespace(root):
    for uri in ("http://www.portalfiscal.inf.br/nfe", "http://portalfiscal.inf.br"):
        ns = {"ns": uri}
        if root.find('.//ns:emit', ns) is not None:
            return ns
    return {"ns": "http://www.portalfiscal.inf.br/nfe"}

# Permite que seu Frontend converse com o Backend sem problemas de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/processar-xml")
async def processar_xml(
    file: UploadFile = File(...), 
    pct_fixo: float = 15.0, 
    pct_simples: float = 8.32,  # Alíquota do Simples Nacional
    pct_cartao: float = 3.0,   # Taxa da maquininha
    pct_lucro: float = 20.0
):
    # Validar se o arquivo é um XML
    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="O arquivo enviado deve ser um XML.")
    
    try:
        conteudo = await file.read()
        root = ET.fromstring(conteudo)
        ns = obter_namespace(root)

        # 1. Extração do Emitente (Fornecedor)
        emitente = root.find('.//ns:emit', ns)
        if emitente is None:
            raise HTTPException(status_code=400, detail="Estrutura de emitente inválida no XML.")
            
        fornecedor = {
            "cnpj": emitente.find('ns:CNPJ', ns).text if emitente.find('ns:CNPJ', ns) is not None else "CPF",
            "razao_social": emitente.find('ns:xNome', ns).text
        }
        
        # 2. Captura dos Totais para Rateio
        total_nota = root.find('.//ns:total/ns:ICMSTot', ns)
        v_prod_total = float(total_nota.find('ns:vProd', ns).text or 0)
        v_frete_total = float(total_nota.find('ns:vFrete', ns).text or 0)
        v_seg_total = float(total_nota.find('ns:vSeg', ns).text or 0)
        v_outro_total = float(total_nota.find('ns:vOutro', ns).text or 0)
        despesas_globais_total = v_frete_total + v_seg_total + v_outro_total
        
        # 3. Lógica do Markup Multiplicador (Simples Nacional + Cartão = Variáveis)
        pct_variavel_total = pct_simples + pct_cartao
        soma_percentuais = (pct_fixo + pct_variavel_total + pct_lucro) / 100
        
        if soma_percentuais >= 1:
            raise HTTPException(status_code=400, detail="A soma das margens operacionais e lucro não pode atingir 100%.")
            
        produtos = []
        
        # 4. Processamento dos Itens
        for det in root.findall('.//ns:det', ns):
            prod = det.find('ns:prod', ns)
            imposto = det.find('ns:imposto', ns)
            
            v_prod_item = float(prod.find('ns:vProd', ns).text)
            qtd = float(prod.find('ns:qCom', ns).text)
            
            # Rateio do Frete/Seguro proporcional
            proporcao = v_prod_item / v_prod_total if v_prod_total > 0 else 0
            frete_rateado = despesas_globais_total * proporcao
            
            # Impostos agregados na compra (IPI / ST)
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
            
            # Cálculo do Preço de Venda utilizando Markup
            preco_venda_sugerido = custo_unitario_real / (1 - soma_percentuais)
            
            produtos.append({
                "codigo": prod.find('ns:cProd', ns).text,
                "descricao": prod.find('ns:xProd', ns).text,
                "custo_unitario_xml": float(prod.find('ns:vUnCom', ns).text),
                "custo_unitario_real": round(custo_unitario_real, 2),
                "preco_venda_sugerido": round(preco_venda_sugerido, 2)
            })
            
        return {
            "fornecedor": fornecedor,
            "configuracoes_aplicadas": {
                "despesas_fixas_pct": pct_fixo,
                "simples_nacional_pct": pct_simples,
                "cartao_pct": pct_cartao,
                "lucro_desejado_pct": pct_lucro
            },
            "produtos": produtos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o XML: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
