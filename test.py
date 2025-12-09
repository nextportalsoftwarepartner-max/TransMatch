from transformers import pipeline


def output_rawdata(text):
    # # To output the raw data from "text"
    output_path = r"D:\CHIANWEILON\Software_Dev\TransMatch\Sample\OUTPUT_TEXT\OUTPUT_TEXT_.txt"
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(text)


with pdfplumber.open("D:\CHIANWEILON\Software_Dev\TransMatch\Sample\PDF\RHB_sample_1.pdf") as pdf:
    for page_no, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()                # clean, line-preserved text
        table = page.extract_table()              # automatic table extraction (list of rows)
        print(f"--- Page {page_no} ---")
        output_rawdata(text)