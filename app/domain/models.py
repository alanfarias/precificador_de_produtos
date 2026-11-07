from dataclasses import dataclass


@dataclass(frozen=True)
class Supplier:
    cnpj: str
    razao_social: str | None


@dataclass(frozen=True)
class InvoiceItem:
    codigo_interno: str
    codigo: str
    descricao: str | None
    valor_produtos: float
    quantidade: float
    custo_unitario_xml: float
    valor_ipi: float
    valor_icms_st: float


@dataclass(frozen=True)
class Invoice:
    fornecedor: Supplier
    valor_produtos_total: float
    despesas_globais: float
    produtos: tuple[InvoiceItem, ...]
