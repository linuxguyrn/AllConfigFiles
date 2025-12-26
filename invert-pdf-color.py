#!/usr/bin/env python3
# author of this script: reddit.com/u/Infinite-End3921
# context: reddit.com/r/pdf/comments/1nstdio/online_pdf_color_inverter_works_perfectly_but_im/
# usage: 
#   pip install pikepdf
#   python invert_pdf.py input.pdf output.pdf
import sys
import pikepdf
from pikepdf import Dictionary, Array, Name, Stream

def wrap_page_into_form(pdf, page):
    box = page.get("/MediaBox")
    x0, y0, x1, y1 = [float(v) for v in box]
    w, h = x1 - x0, y1 - y0

    contents = page.get("/Contents")
    if contents is None:
        original_ops = b""
    else:
        streams = contents if isinstance(contents, Array) else [contents]
        parts = []
        for s in streams:
            try:
                parts.append(s.read_bytes())
            except Exception:
                pass
        original_ops = b"\n".join(parts)

    res = page.get("/Resources") or Dictionary()
    if not isinstance(res, Dictionary):
        res = Dictionary(res)

    form = Stream(pdf, original_ops)
    form["/Type"] = Name("/XObject")
    form["/Subtype"] = Name("/Form")
    form["/BBox"] = Array([x0, y0, x1, y1])
    form["/Resources"] = res
    form["/Group"] = Dictionary({
        "/S": Name("/Transparency"),
        "/I": False,
        "/K": False,
        "/CS": Name("/DeviceRGB"),
    })
    form_ref = pdf.make_indirect(form)

    xobj = res.get("/XObject") or Dictionary()
    xobj[Name("/Fm0")] = form_ref
    res["/XObject"] = xobj
    page.Resources = res

    return (w, h)

def invert_pdf(inp, outp):
    with pikepdf.open(inp) as pdf:
        gs = pdf.make_indirect(Dictionary({
            "/Type": Name("/ExtGState"),
            "/BM": Name("/Difference"),
        }))

        for page in pdf.pages:
            dims = wrap_page_into_form(pdf, page)
            if dims is None:
                continue
            w, h = dims

            grp = page.get("/Group") or Dictionary()
            grp["/S"] = Name("/Transparency")
            grp["/I"] = False
            grp["/K"] = False
            grp["/CS"] = Name("/DeviceRGB")
            page["/Group"] = grp

            res = page.get("/Resources") or Dictionary()
            extg = res.get("/ExtGState") or Dictionary()
            extg[Name("/GSINV")] = gs
            res["/ExtGState"] = extg
            page.Resources = res

            bg_ops = f"q\n1 1 1 rg\n0 0 {w} {h} re\nf\nQ\n"
            bg_stream = Stream(pdf, bg_ops.encode("ascii"))

            draw_form_stream = Stream(pdf, b"q\n/Fm0 Do\nQ\n")

            overlay_ops = (
                "q\n"
                f"0 0 {w} {h} re\n"
                "/GSINV gs\n"
                "1 1 1 rg\n"
                "f\n"
                "Q\n"
            )
            overlay_stream = Stream(pdf, overlay_ops.encode("ascii"))

            page.Contents = Array([bg_stream, draw_form_stream, overlay_stream])

        pdf.save(outp)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python invert_pdf.py input.pdf output.pdf")
        sys.exit(1)
    invert_pdf(sys.argv[1], sys.argv[2])
    print(f"✓ Wrote: {sys.argv[2]}")


