"""Rewrite an openpyxl workbook with xlsxwriter (shared strings) so it is much smaller to email."""
import sys, openpyxl, xlsxwriter
src, dst = sys.argv[1:3]
wb = openpyxl.load_workbook(src)
out = xlsxwriter.Workbook(dst, {"strings_to_numbers": False, "strings_to_urls": False})
out.set_properties({"author": wb.properties.creator or "", "comments": wb.properties.description or ""})
head = out.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E79"})
red = out.add_format({"bold": True, "font_color": "#C00000"})
wrap = out.add_format({"text_wrap": True, "valign": "top"})
for ws in wb.worksheets:
    o = out.add_worksheet(ws.title)
    for col, dim in ws.column_dimensions.items():
        if dim.width:
            i = openpyxl.utils.column_index_from_string(col) - 1
            o.set_column(i, i, dim.width)
    for r, row in enumerate(ws.iter_rows(values_only=True)):
        for c, v in enumerate(row):
            if v is None: continue
            fmt = None
            if ws.title == "README":
                fmt = red if r == 0 else wrap if r == 1 else None
            elif r == 0:
                fmt = head
            o.write(r, c, v, fmt)
    if ws.title == "README":
        o.set_row(1, 75)
    else:
        o.freeze_panes(1, 0)
        o.autofilter(0, 0, max(ws.max_row - 1, 0), max(ws.max_column - 1, 0))
    o.set_header("&C" + (ws.oddHeader.center.text or ""))
    o.set_footer("&C" + (ws.oddFooter.center.text or ""))
out.close()
