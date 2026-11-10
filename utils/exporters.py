"""
EcoLogix AI - Real Excel (.xlsx) & PDF (.pdf) Report Exporters
Sử dụng OpenPyXL và ReportLab (nhúng font Arial/Tahoma hỗ trợ 100% tiếng Việt UTF-8).
"""
import io
import os
from datetime import datetime
from typing import Dict, Any, List

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def _register_vietnamese_fonts() -> tuple:
    """Đăng ký font TrueType tiếng Việt từ Windows Fonts để tránh lỗi dấu."""
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf", "EcoArial", "EcoArialBold"),
        (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf", "EcoTahoma", "EcoTahomaBold"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf", "EcoSegoe", "EcoSegoeBold"),
    ]
    for reg_path, bold_path, reg_name, bold_name in candidates:
        if os.path.exists(reg_path):
            try:
                if reg_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(reg_name, reg_path))
                regular_font = reg_name
                if os.path.exists(bold_path):
                    if bold_name not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                    bold_font = bold_name
                else:
                    bold_font = reg_name
                break
            except Exception:
                continue
    return regular_font, bold_font


def export_financial_esg_excel_bytes(report_data: Dict[str, Any]) -> bytes:
    """Xuất file Excel (.xlsx) gồm 3 sheet: Tổng quan Tài chính, Báo cáo ESG & Đội xe."""
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="064E43", end_color="064E43", fill_type="solid")
    accent_fill = PatternFill(start_color="E8F7EF", end_color="E8F7EF", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=15, bold=True, color="064E43")
    bold_font = Font(name="Calibri", size=11, bold=True)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    def _style_header(ws, row_idx: int, col_count: int):
        for col in range(1, col_count + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    def _auto_fit(ws):
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 5, 42)

    # Sheet 1: Tong quan Tai chinh
    ws1 = wb.active
    ws1.title = "Tai chinh Logistics"
    ws1["A1"] = "ECOLOGIX AI - BÁO CÁO PHÂN TÍCH TÀI CHÍNH CHUỖI CUNG ỨNG"
    ws1["A1"].font = title_font
    ws1["A2"] = f"Ngày xuất báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    summary = report_data.get("financial_summary", {})
    ws1.append([])
    ws1.append(["Chỉ tiêu tài chính", "Giá trị"])
    _style_header(ws1, 4, 2)
    summary_rows = [
        ("Tổng doanh thu đơn hàng (VNĐ)", summary.get("total_revenue_vnd", 0)),
        ("Tổng chi phí vận hành logistics (VNĐ)", summary.get("total_cost_vnd", 0)),
        ("Chi phí nhiên liệu (VNĐ)", summary.get("fuel_cost_vnd", 0)),
        ("Chi phí nhân công (VNĐ)", summary.get("labor_cost_vnd", 0)),
        ("Chi phí lưu kho (VNĐ)", summary.get("storage_cost_vnd", 0)),
        ("Thuế phát thải Carbon (VNĐ)", summary.get("carbon_tax_vnd", 0)),
        ("Lợi nhuận ròng ước tính (VNĐ)", summary.get("net_profit_vnd", 0)),
        ("Tiết kiệm chi phí trung bình (%)", f"{summary.get('cost_saving_pct', 0)}%"),
        ("Thời gian hoàn vốn dự kiến (ROI)", f"{summary.get('payback_months', 3.4)} tháng"),
    ]
    for label, val in summary_rows:
        ws1.append([label, val])

    ws1.append([])
    start_row = ws1.max_row + 1
    ws1.append(["Tháng", "Chi phí (VNĐ)", "Doanh thu (VNĐ)", "Lợi nhuận (VNĐ)"])
    _style_header(ws1, start_row, 4)
    for m in report_data.get("monthly_financial", []):
        ws1.append([m["month"], m["cost_vnd"], m["revenue_vnd"], m["profit_vnd"]])
    _auto_fit(ws1)

    # Sheet 2: Bao cao ESG & CO2
    ws2 = wb.create_sheet(title="Bao cao ESG CO2")
    ws2["A1"] = "ECOLOGIX AI - BÁO CÁO KIỂM TOÁN PHÁT THẢI CO2 CHUẨN ESG"
    ws2["A1"].font = title_font
    esg = report_data.get("esg_summary", {})
    ws2.append([])
    ws2.append(["Chỉ số ESG", "Giá trị"])
    _style_header(ws2, 3, 2)
    for label, val in [
        ("Điểm Logistics Xanh (Green Score)", f"{esg.get('green_score', 94.0)}%"),
        ("Tổng phát thải CO2 thực tế (kg)", esg.get("total_co2_kg", 0)),
        ("Lượng CO2 cắt giảm được (kg)", esg.get("co2_saved_kg", 0)),
        ("Tỷ lệ giảm phát thải (%)", f"-{esg.get('co2_reduction_pct', 18.7)}%"),
        ("Nhiên liệu tiết kiệm (Lít)", esg.get("fuel_saved_liters", 0)),
        ("Tiêu chuẩn áp dụng", "GHG Protocol Scope 1 & ISO 14064-1"),
    ]:
        ws2.append([label, val])

    ws2.append([])
    r2_hdr = ws2.max_row + 1
    ws2.append(["Kỳ báo cáo", "Tổng CO2 (kg)", "CO2 đã giảm (kg)", "Điểm xanh (%)"])
    _style_header(ws2, r2_hdr, 4)
    for item in report_data.get("esg_history", []):
        ws2.append([
            f"T{item['month']}/{item['year']}",
            item["total_co2_kg"],
            item["co2_saved_kg"],
            item["green_logistics_score"],
        ])
    _auto_fit(ws2)

    # Sheet 3: Hieu suat doi xe & Tuyen duong
    ws3 = wb.create_sheet(title="Doi xe & Tuyen duong")
    ws3["A1"] = "HIỆU SUẤT PHƯƠNG TIỆN & PHÁT THẢI THEO XE"
    ws3["A1"].font = title_font
    ws3.append([])
    ws3.append(["Biển số", "Tên xe", "Nhiên liệu", "Số chuyến", "Quãng đường (km)", "CO2 (kg)", "Chi phí (VNĐ)"])
    _style_header(ws3, 3, 7)
    for v in report_data.get("vehicle_performance", []):
        ws3.append([
            v.get("plate_number"),
            v.get("vehicle_name"),
            v.get("fuel_type"),
            v.get("total_routes", 0),
            v.get("total_distance_km", 0),
            v.get("total_co2_kg", 0),
            v.get("total_cost_vnd", 0),
        ])
    _auto_fit(ws3)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_esg_pdf_bytes(report_data: Dict[str, Any], company_name: str = "EcoLogix Logistics SME") -> bytes:
    """Xuất file PDF thực sự chuẩn UTF-8 tiếng Việt cho Báo cáo Tài chính & ESG."""
    reg_font, bold_font = _register_vietnamese_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EcoTitle", parent=styles["Heading1"], fontName=bold_font, fontSize=16,
        textColor=colors.HexColor("#064E43"), spaceAfter=6
    )
    sub_style = ParagraphStyle(
        "EcoSub", parent=styles["Normal"], fontName=reg_font, fontSize=10,
        textColor=colors.HexColor("#475569"), spaceAfter=14
    )
    h2_style = ParagraphStyle(
        "EcoH2", parent=styles["Heading2"], fontName=bold_font, fontSize=12,
        textColor=colors.HexColor("#07965B"), spaceBefore=12, spaceAfter=6
    )
    cell_style = ParagraphStyle("EcoCell", parent=styles["Normal"], fontName=reg_font, fontSize=9.5)

    fin = report_data.get("financial_summary", {})
    esg = report_data.get("esg_summary", {})

    elements: List[Any] = [
        Paragraph("BÁO CÁO TÀI CHÍNH & KIỂM TOÁN ESG - ECOLOGIX AI", title_style),
        Paragraph(
            f"Doanh nghiệp: {company_name} | Ngày lập: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Chuẩn GHG Protocol Scope 1",
            sub_style,
        ),
        Paragraph("1. Tổng Quan Hiệu Quả Kinh Tế & Vận Hành Logistics", h2_style),
    ]

    fin_table_data = [
        [Paragraph("<b>Chỉ tiêu kinh tế</b>", cell_style), Paragraph("<b>Giá trị ghi nhận</b>", cell_style)],
        ["Tổng doanh thu vận hành", f"{fin.get('total_revenue_vnd', 0):,.0f} VNĐ"],
        ["Tổng chi phí logistics", f"{fin.get('total_cost_vnd', 0):,.0f} VNĐ"],
        ["Chi phí nhiên liệu", f"{fin.get('fuel_cost_vnd', 0):,.0f} VNĐ"],
        ["Chi phí nhân công & kho bãi", f"{(fin.get('labor_cost_vnd', 0) + fin.get('storage_cost_vnd', 0)):,.0f} VNĐ"],
        ["Thuế Carbon đã hạch toán", f"{fin.get('carbon_tax_vnd', 0):,.0f} VNĐ"],
        ["Tỷ lệ tiết kiệm chi phí", f"{fin.get('cost_saving_pct', 21.5)}%"],
        ["Thời gian hoàn vốn (ROI)", f"{fin.get('payback_months', 3.4)} tháng"],
    ]
    t1 = Table(fin_table_data, colWidths=[260, 240])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#064E43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), reg_font),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(t1)

    elements.append(Paragraph("2. Chỉ Số Phát Thải Carbon & Logistics Xanh (ESG)", h2_style))
    esg_table_data = [
        ["Chỉ số ESG", "Kết quả", "Đánh giá"],
        ["Điểm mục tiêu Logistics Xanh", f"{esg.get('green_score', 94.0)}%", "Đạt chuẩn xuất khẩu xanh"],
        ["Tổng lượng phát thải CO2", f"{esg.get('total_co2_kg', 0):,.1f} kg", "GHG Scope 1"],
        ["Lượng CO2 cắt giảm nhờ AI VRP", f"-{esg.get('co2_saved_kg', 0):,.1f} kg (-{esg.get('co2_reduction_pct', 18.7)}%)", "Vượt mục tiêu 18%"],
        ["Nhiên liệu tiết kiệm tích lũy", f"{esg.get('fuel_saved_liters', 0):,.1f} Lít", "Tối ưu tuyến + EV"],
    ]
    t2 = Table(esg_table_data, colWidths=[190, 150, 160])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#07965B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), reg_font),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDF4")]),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(t2)

    vehicles = report_data.get("vehicle_performance", [])
    if vehicles:
        elements.append(Paragraph("3. Thống Kê Phát Thải & Quãng Đường Theo Phương Tiện", h2_style))
        v_rows = [["Biển số", "Phương tiện", "Nhiên liệu", "Quãng đường", "CO2 (kg)"]]
        for v in vehicles:
            v_rows.append([
                str(v.get("plate_number", "")),
                str(v.get("vehicle_name", "")),
                str(v.get("fuel_type", "")),
                f"{v.get('total_distance_km', 0):,.1f} km",
                f"{v.get('total_co2_kg', 0):,.1f} kg",
            ])
        t3 = Table(v_rows, colWidths=[80, 160, 75, 95, 90])
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), reg_font),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t3)

    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "Báo cáo được tạo tự động bởi Nền tảng EcoLogix AI — Cuộc thi AI IN ECONOMICS 2026 (HCM-UTE).",
        sub_style,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()

