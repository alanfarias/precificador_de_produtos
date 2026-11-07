from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.domain.pricing import PricingError, calcular_precos
from app.infrastructure.nfe_xml import NFeXmlError, ler_nfe

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
XML_DIR = PROJECT_ROOT / "xml"
MAX_XML_SIZE = 10 * 1024 * 1024


@router.post("/api/processar-xml")
def processar_xml(
    file: UploadFile | None = File(default=None),
    filename: str | None = Form(default=None),
    pct_fixo: float = Form(default=15.0, ge=0, le=100),
    pct_simples: float = Form(default=8.32, ge=0, le=100),
    pct_cartao: float = Form(default=3.0, ge=0, le=100),
    pct_lucro: float = Form(default=20.0, ge=0, le=100),
) -> dict[str, object]:
    if file is None and not filename:
        raise HTTPException(
            status_code=400,
            detail=(
                "Envie um XML em multipart/form-data ou informe o nome do "
                "arquivo na pasta xml/ do servidor."
            ),
        )

    try:
        if file is not None:
            if not file.filename or not file.filename.lower().endswith(".xml"):
                raise HTTPException(
                    status_code=400,
                    detail="O arquivo enviado deve ser um XML.",
                )
            content = file.file.read(MAX_XML_SIZE + 1)
            if len(content) > MAX_XML_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="O arquivo XML excede o limite de 10 MB.",
                )
        else:
            if filename is None:
                raise HTTPException(
                    status_code=400,
                    detail="Informe o nome do arquivo XML.",
                )
            if not filename.lower().endswith(".xml"):
                raise HTTPException(
                    status_code=400,
                    detail="O nome do arquivo informado deve terminar em .xml.",
                )
            path = (XML_DIR / filename).resolve()
            if path.parent != XML_DIR.resolve():
                raise HTTPException(
                    status_code=400,
                    detail="Arquivo fora do diretório permitido.",
                )
            if not path.is_file():
                raise HTTPException(
                    status_code=404,
                    detail=f"Arquivo XML não encontrado na pasta xml/: {filename}",
                )
            with path.open("rb") as xml_file:
                content = xml_file.read(MAX_XML_SIZE + 1)
            if len(content) > MAX_XML_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="O arquivo XML excede o limite de 10 MB.",
                )

        invoice = ler_nfe(content)
        return calcular_precos(
            invoice,
            pct_fixo=pct_fixo,
            pct_simples=pct_simples,
            pct_cartao=pct_cartao,
            pct_lucro=pct_lucro,
        )
    except HTTPException:
        raise
    except NFeXmlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PricingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível ler o arquivo XML.",
        ) from exc
    finally:
        if file is not None:
            file.file.close()
