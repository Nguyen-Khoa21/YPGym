from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.config import get_settings


def format_vnd(amount: Decimal | int) -> str:
    return f"VND {amount:,.0f}"


class InvoicePdfService:
    def __init__(self) -> None:
        settings = get_settings()
        self.storage_dir = Path(settings.INVOICE_STORAGE_DIR)

    def build_invoice_number(self, payment_id: UUID, created_at: datetime | None = None) -> str:
        date_part = (created_at or datetime.now(UTC)).strftime("%Y%m%d")
        return f"YPG-{date_part}-{str(payment_id)[:8].upper()}"

    def generate_pdf(
        self,
        *,
        invoice_number: str,
        member_name: str,
        member_email: str,
        plan_name: str,
        amount,
        discount_amount,
        transaction_date: datetime,
        membership_start_date,
        membership_expiry_date,
        product_type: str = "membership",
        product_name: str | None = None,
        service_start_at: datetime | None = None,
        service_end_at: datetime | None = None,
        discount_details: dict | None = None,
    ) -> str:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = self.storage_dir / f"{invoice_number}.pdf"

        document = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4

        document.setTitle(invoice_number)
        document.setFont("Helvetica-Bold", 22)
        document.drawString(24 * mm, height - 28 * mm, "YPGym Invoice")

        document.setFont("Helvetica", 10)
        document.drawString(24 * mm, height - 38 * mm, "YPGym Fitness Center")
        document.drawString(
            24 * mm,
            height - 44 * mm,
            "Class booking receipt" if product_type == "class_booking" else "Membership billing receipt",
        )

        document.setFont("Helvetica-Bold", 11)
        document.drawRightString(width - 24 * mm, height - 30 * mm, invoice_number)
        document.setFont("Helvetica", 10)
        document.drawRightString(
            width - 24 * mm,
            height - 38 * mm,
            transaction_date.strftime("%d %b %Y, %H:%M"),
        )

        y = height - 65 * mm
        document.setFont("Helvetica-Bold", 12)
        document.drawString(24 * mm, y, "Bill to")
        document.setFont("Helvetica", 10)
        document.drawString(24 * mm, y - 8 * mm, member_name)
        document.drawString(24 * mm, y - 14 * mm, member_email)

        y -= 34 * mm
        document.setFont("Helvetica-Bold", 11)
        document.drawString(24 * mm, y, "Class" if product_type == "class_booking" else "Plan")
        document.drawString(92 * mm, y, "Session" if product_type == "class_booking" else "Coverage")
        document.drawRightString(width - 24 * mm, y, "Amount")
        document.line(24 * mm, y - 3 * mm, width - 24 * mm, y - 3 * mm)

        document.setFont("Helvetica", 10)
        if product_type == "class_booking":
            coverage = (
                f"{service_start_at.strftime('%d %b %Y %H:%M')} - "
                f"{service_end_at.strftime('%H:%M')}"
            )
        else:
            coverage = (
                f"{membership_start_date.strftime('%d %b %Y')} - "
                f"{membership_expiry_date.strftime('%d %b %Y')}"
            )
        document.drawString(24 * mm, y - 12 * mm, product_name or plan_name)
        document.drawString(92 * mm, y - 12 * mm, coverage)
        pricing = (discount_details or {}).get("pricing", {})
        base_price = pricing.get("base_price", amount)
        document.drawRightString(width - 24 * mm, y - 12 * mm, format_vnd(Decimal(str(base_price))))

        y -= 34 * mm
        document.setFont("Helvetica", 10)
        applied_percent = pricing.get("applied_discount_percent")
        discount_label = f"Discount ({applied_percent}%)" if applied_percent is not None else "Discount"
        document.drawRightString(width - 58 * mm, y, discount_label)
        document.drawRightString(width - 24 * mm, y, format_vnd(discount_amount))
        if discount_details and discount_details.get("available"):
            document.setFont("Helvetica", 8)
            benefit_result = (
                "attendance discount applied"
                if pricing.get("attendance_benefit_selected")
                else "plan discount applied"
            )
            document.drawString(
                24 * mm,
                y - 10 * mm,
                f"Attendance benefit: {discount_details['attended_days']}/{discount_details['period_days']} days "
                f"({discount_details['attendance_percentage']}%), {discount_details['period_start']} to "
                f"{discount_details['period_end']}; {benefit_result} under better-of rule.",
            )
        document.setFont("Helvetica-Bold", 12)
        document.drawRightString(width - 58 * mm, y - 10 * mm, "Paid")
        document.drawRightString(width - 24 * mm, y - 10 * mm, format_vnd(amount))

        document.setFont("Helvetica", 9)
        document.setFillColorRGB(0.35, 0.35, 0.35)
        document.drawString(
            24 * mm,
            24 * mm,
            "This invoice is generated by the YPGym billing system.",
        )
        document.save()

        return str(pdf_path)
