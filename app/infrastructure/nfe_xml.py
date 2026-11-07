import math
from xml.etree import ElementTree

from defusedxml import ElementTree as SafeElementTree
from defusedxml.common import DefusedXmlException

from app.domain.models import Invoice, InvoiceItem, Supplier

NFE_NAMESPACES = (
    "http://www.portalfiscal.inf.br/nfe",
    "http://portalfiscal.inf.br",
)


class NFeXmlError(ValueError):
    """Raised when an NF-e XML is invalid or missing required data."""


def _namespace(root: ElementTree.Element) -> dict[str, str]:
    for uri in NFE_NAMESPACES:
        namespace = {"ns": uri}
        if root.find(".//ns:emit", namespace) is not None:
            return namespace
    return {"ns": NFE_NAMESPACES[0]}


def _required_text(
    element: ElementTree.Element,
    path: str,
    namespace: dict[str, str],
    label: str,
) -> str:
    node = element.find(path, namespace)
    if node is None or node.text is None or not node.text.strip():
        raise NFeXmlError(f"Campo obrigatório ausente ou inválido no XML: {label}.")
    return node.text.strip()


def _number(
    element: ElementTree.Element,
    path: str,
    namespace: dict[str, str],
    label: str,
    *,
    default: float | None = None,
) -> float:
    node = element.find(path, namespace)
    if node is None or node.text is None or not node.text.strip():
        if default is not None:
            return default
        raise NFeXmlError(f"Campo obrigatório ausente ou inválido no XML: {label}.")
    return _parse_number(node.text, label)


def _parse_number(value: str, label: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise NFeXmlError(f"Valor numérico inválido no XML: {label}.") from exc
    if not math.isfinite(number):
        raise NFeXmlError(f"Valor numérico inválido no XML: {label}.")
    return number


def ler_nfe(content: bytes) -> Invoice:
    try:
        root = SafeElementTree.fromstring(content, forbid_dtd=True)
    except (ElementTree.ParseError, DefusedXmlException, ValueError) as exc:
        raise NFeXmlError("O arquivo não contém um XML válido e seguro.") from exc

    namespace = _namespace(root)
    emitente = root.find(".//ns:emit", namespace)
    if emitente is None:
        raise NFeXmlError("Estrutura de emitente inválida no XML.")

    cnpj_node = emitente.find("ns:CNPJ", namespace)
    fornecedor = Supplier(
        cnpj=(
            cnpj_node.text.strip()
            if cnpj_node is not None and cnpj_node.text
            else "CPF"
        ),
        razao_social=emitente.findtext("ns:xNome", default=None, namespaces=namespace),
    )

    total_nota = root.find(".//ns:total/ns:ICMSTot", namespace)
    if total_nota is None:
        raise NFeXmlError("Estrutura de totais inválida no XML.")

    valor_produtos_total = _number(
        total_nota, "ns:vProd", namespace, "total de produtos"
    )
    despesas_globais = sum(
        _number(total_nota, f"ns:{field}", namespace, field, default=0.0)
        for field in ("vFrete", "vSeg", "vOutro")
    )

    produtos: list[InvoiceItem] = []
    for detail in root.findall(".//ns:det", namespace):
        product = detail.find("ns:prod", namespace)
        if product is None:
            raise NFeXmlError("Estrutura de produto inválida no XML.")
        taxes = detail.find("ns:imposto", namespace)

        codigo_interno = _required_text(product, "ns:cProd", namespace, "cProd")
        ean = product.find("ns:cEAN", namespace)
        if ean is None or not ean.text:
            ean = product.find("ns:cEANTrib", namespace)
        codigo = (
            ean.text.strip()
            if ean is not None and ean.text and ean.text.strip()
            else codigo_interno
        )

        valor_ipi = 0.0
        valor_icms_st = 0.0
        if taxes is not None:
            ipi = taxes.find(".//ns:IPI/ns:IPITrib/ns:vIPI", namespace)
            if ipi is not None and ipi.text:
                valor_ipi = _parse_number(ipi.text, "vIPI")
            icms_st = taxes.find(".//ns:ICMS//ns:vICMSST", namespace)
            if icms_st is not None and icms_st.text:
                valor_icms_st = _parse_number(icms_st.text, "vICMSST")

        produtos.append(
            InvoiceItem(
                codigo_interno=codigo_interno,
                codigo=codigo,
                descricao=product.findtext(
                    "ns:xProd", default=None, namespaces=namespace
                ),
                valor_produtos=_number(
                    product, "ns:vProd", namespace, "vProd do item"
                ),
                quantidade=_number(product, "ns:qCom", namespace, "qCom"),
                custo_unitario_xml=_number(
                    product, "ns:vUnCom", namespace, "vUnCom"
                ),
                valor_ipi=valor_ipi,
                valor_icms_st=valor_icms_st,
            )
        )

    return Invoice(
        fornecedor=fornecedor,
        valor_produtos_total=valor_produtos_total,
        despesas_globais=despesas_globais,
        produtos=tuple(produtos),
    )
