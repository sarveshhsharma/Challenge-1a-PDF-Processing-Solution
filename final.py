import fitz  # PyMuPDF
import pdfplumber
from collections import Counter,defaultdict
import re
import json
import os

#This code filters headings based on font size and headings have same font size as that of paragraph based on

#left/centered check - alignment
#distance from above, below
#bold or italic 
#distance from left
#min occured gap between 2 lines 
#font size
#ignores tables

# Most frequent element
print(f"Processing Started")

def most_frequent(numbers):
    numbers = [n for n in numbers if n is not None]
    if not numbers:
        return None
    sorted_numbers = sorted(numbers)
    count = Counter(sorted_numbers)
    most_common_num, freq = count.most_common(1)[0]
    return most_common_num

# Extract font style
def get_font_info(span):
    font = span.get("font", "").lower()
    size = round(span.get("size", 0))

    # Debug: print the font name if needed
    # print("Font Detected:", font)

    style = "normal"

    # Expanded bold and italic keywords
    bold_keywords = ["bold", "bolder", "semibold", "extrabold", "boldmt", "demibold", "black"]
    italic_keywords = ["italic", "oblique", "it", "slanted"]

    is_bold = any(bk in font for bk in bold_keywords)
    is_italic = any(ik in font for ik in italic_keywords)

    if is_bold and is_italic:
        style = "bold-italic"
    elif is_bold:
        style = "bold"
    elif is_italic:
        style = "italic"

    return font, size, style

# Determine alignment
def get_alignment(x0, x1, page_width, margin=20): 
    center = (x0 + x1) / 2

    if abs(x0) <= margin:
        return "left"
    elif abs(page_width - x1) <= margin:
        return "right"
    elif abs(center - page_width / 2) <= margin:
        return "center"
    elif x0 > margin and center < page_width * 0.55:
        return "left-centered"
    return "unknown"

# Check if a line box overlaps with any table box
def is_in_table(y0, y1, x0, x1, table_bboxes):
    for table in table_bboxes:
        tx0, ty0, tx1, ty1 = table
        if (x1 > tx0 and x0 < tx1) and (y1 > ty0 and y0 < ty1):
            return True
    return False

# Final combined extractor
def solve(pdf_path, threshold):
    doc = fitz.open(pdf_path)
    results_all_pages = []
    most_frequent_distance_between_2_lines_per_page = []
    header_lines_greater_than_threshold = []  # NEW LIST ADDED

    # Use pdfplumber to detect table boxes
    with pdfplumber.open(pdf_path) as plumber_pdf:
        for page_num, page in enumerate(doc):
            page_width = page.rect.width
            blocks = page.get_text("dict")["blocks"]

            # Extract table bounding boxes using pdfplumber
            plumber_page = plumber_pdf.pages[page_num]
            table_bboxes = []
            for table in plumber_page.find_tables():
                if table.bbox:
                    table_bboxes.append(table.bbox)  # (x0, top, x1, bottom)

            lines_data = []
            count = 0
            for block in blocks:
                if block['type'] != 0:
                    continue

                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    # Line bounding box
                    x0 = min(span["bbox"][0] for span in spans)
                    y0 = min(span["bbox"][1] for span in spans)
                    x1 = max(span["bbox"][2] for span in spans)
                    y1 = max(span["bbox"][3] for span in spans)

                    # ADD HEADER LINE IF SIZE >= THRESHOLD
                    line_text = " ".join([span["text"] for span in spans]).strip()               
                    y0_avg = sum([span["bbox"][1] for span in spans]) / len(spans)

                    alignment = get_alignment(x0, x1, page_width)
                    first_span = spans[0]
                    font_name, font_size, font_style = get_font_info(first_span)
                    leftmost_x = min(span["bbox"][0] for span in spans)  

                    if font_size >= threshold:
                        header_lines_greater_than_threshold.append({
                            "text": line_text,
                            "line-no":count,
                            "page": page_num +1,
                            "font_size": font_size,
                            "left_distance": round(leftmost_x, 2),
                        })
                    count = count +1
                    # Skip line if inside table
                    if is_in_table(y0, y1, x0, x1, table_bboxes):
                        continue

                    lines_data.append((y0_avg, line_text, alignment, font_size, font_style, leftmost_x))

            # Sort lines vertically
            lines_data.sort(key=lambda x: x[0])

            above_distances = []
            below_distances = []
            enriched_lines = []

            for i, (y0, text, alignment, size, style, left_x) in enumerate(lines_data):
                above_dist = None
                below_dist = None

                if i > 0:
                    above_dist = y0 - lines_data[i - 1][0]
                    if round(above_dist) != 0:
                        above_distances.append(round(above_dist))

                if i < len(lines_data) - 1:
                    below_dist = lines_data[i + 1][0] - y0
                    if round(below_dist) != 0:
                        below_distances.append(round(below_dist))
                if(text == ""): continue
                enriched_line = {
                    "page": page_num + 1,
                    "text": text,
                    "alignment": alignment,
                    "above_dist": round(above_dist, 2) if above_dist else None,
                    "below_dist": round(below_dist, 2) if below_dist else None,
                    "font_size": size,
                    "font-style": style,
                    "left_distance": round(left_x, 2),
                    "line-no": i
                }

                enriched_lines.append(enriched_line)


            most_frequent_distance_between_2_lines_per_page.append(most_frequent(above_distances))
            most_frequent_distance_between_2_lines_per_page.append(most_frequent(below_distances))
            results_all_pages.extend(enriched_lines)

    global_most_frequent = most_frequent(most_frequent_distance_between_2_lines_per_page)
    font_sizes = [r['font_size'] for r in results_all_pages]
    most_common_font_size = most_frequent(font_sizes)
    return results_all_pages, global_most_frequent, most_common_font_size, header_lines_greater_than_threshold


#threshold based on font size (font size that repeats the most)
#a = most repeated font size
#b = second most repeated font size
def get_trashold(a, a1, b, b1):
    if abs(b1 - a1 / 2) <= 1:
        return max(a, b) + 1
    return a + 1


def get_fonts_and_sizes(pdf_path):
    doc = fitz.open(pdf_path)
    font_size_counter = Counter()
    font_counter = Counter()
    font_size_mapping = defaultdict(set)

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_name = span["font"]
                    font_size = round(span["size"])

                    font_counter[font_name] += 1
                    font_size_counter[font_size] += 1
                    font_size_mapping[font_name].add(font_size)

    most_common_font = font_counter.most_common(1)[0]

    counter = 0
    font_size1 = 0
    font_count1 = 0
    font_size2 = 0
    font_count2 = 0
    #print("All Font Sizes and Their Frequencies:")
    for size, count in font_size_counter.most_common():
        if counter == 0:
            font_size1 = size
            font_count1 = count
        elif counter == 1:
            font_size2 = size
            font_count2 = count
        counter += 1
        #print(f"Font Size: {size}, Count: {count}")

    # print("\nMost Common Font:")
    # print(f"Font: {most_common_font[0]}, Occurrences: {most_common_font[1]}")
    # print(f"Font Sizes used by this font: {sorted(font_size_mapping[most_common_font[0]])}")
    # print(str(font_size1) + " " + str(font_size2))
    threshold = get_trashold(font_size1, font_count1, font_size2, font_count2)
    # print("Threshold: " + str(threshold))
    return threshold

# === Example Usage ===
pdf_path = "./pdf/file05.pdf"
threshold = get_fonts_and_sizes(pdf_path)
results, global_threshold, most_common_font_size, header_lines_greater_than_threshold = solve(pdf_path, threshold)


font_sizes = [r['font_size'] for r in results]

# print(f"Global Most Frequent Line GAP: {global_threshold}")
# print(f"Most Occurred Font Size: {most_common_font_size}")
# print("-" * 60)

# Step 1: Collect lines to be printed
printed_keys = set()
candidates = []

# Header lines
for r in header_lines_greater_than_threshold:
    key = (r['page'], r['line-no'])
    if key in printed_keys:
        continue
    printed_keys.add(key)
    candidates.append({
        "page": r['page'],
        "line-no": r['line-no'],
        "text": r['text'],
        "font_size": r['font_size'],
        "alignment": None,
        "font_style": None,
        "source": "header"
    })

# Styled & lonely or left-shifted lines
for i, r in enumerate(results):
    key = (r['page'], r['line-no'])
    if key in printed_keys:
        continue

    if r['alignment'] == "unknown":
        continue

    is_styled = r['font-style'] in {"bold", "bold-italic"}
    is_large_enough = (round(r['font_size'])+1 >= most_common_font_size)
    is_lonely = (r['above_dist'] is None) or (round(r['above_dist']) > global_threshold)

    left_condition = False
    if i + 1 < len(results):
        left_condition = round(r['left_distance']) > round(results[i + 1]['left_distance'])

    if is_styled and is_large_enough and (is_lonely or left_condition):
        printed_keys.add(key)
        candidates.append({
            "page": r['page'],
            "line-no": r['line-no'],
            "text": r['text'],
            "font_size": r['font_size'],
            "alignment": r['alignment'],
            "font_style": r['font-style'],
            "source": "styled"
        })

# Step 2: Sort candidates by (page, line-no)
candidates.sort(key=lambda x: (x['page'], x['line-no']))

# Step 3: Merge adjacent lines only if criteria match
merged = []
i = 0
while i < len(candidates):
    current = candidates[i]
    merged_text = current['text']
    current_font_size = current['font_size']
    current_alignment = current.get('alignment')
    current_font_style = current.get('font_style')
    current_page = current['page']
    last_line_no = current['line-no']

    j = i + 1
    while j < len(candidates):
        next_line = candidates[j]
        same_page = next_line['page'] == current_page
        consecutive = next_line['line-no'] == last_line_no + 1
        same_style = next_line.get('font_style') == current_font_style
        same_align = next_line.get('alignment') == current_alignment
        same_font_size = next_line['font_size'] == current_font_size

        if same_page and consecutive and same_style and same_align and same_font_size:
            merged_text += " " + next_line['text']
            last_line_no = next_line['line-no']
            j += 1
        else:
            break

    merged.append({
        "page": current_page,
        "line-no": last_line_no,
        "text": merged_text.strip(),
        "font_size": current_font_size,
        "alignment": current_alignment,
        "font_style": current_font_style
    })
    i = j

# Step 4: Print merged results
unique_sizes = sorted({r['font_size'] for r in merged}, reverse=True)
size_to_level = {size: f"H{idx + 1}" for idx, size in enumerate(unique_sizes)}

# Separate page 1 and page >=2 headers
page1_items = [r for r in merged if r["page"] == 1]
other_pages = [r for r in merged if r["page"] > 1]

# Get the largest font size item on page 1
page1_h1 = None
if page1_items:
    page1_h1 = max(page1_items, key=lambda x: x["font_size"])

# Get font sizes from pages >= 2 and sort descending
other_sizes = sorted({r["font_size"] for r in other_pages}, reverse=True)
size_to_level = {size: f"H{idx + 1}" for idx, size in enumerate(other_sizes)}

# Print result in required format
first = True

title = page1_h1['text'].replace('\n', ' ').strip() if page1_h1 else ""

# Build the outline list
outline = []

# Add the page 1 H1 entry if it exists
if page1_h1:
    outline.append({
        "level": "H1",
        "text": title,
        "page": page1_h1["page"]
    })

# Add other headings
for r in other_pages:
    text_clean = r['text'].replace('\n', ' ').strip()
    level = size_to_level[r['font_size']]
    outline.append({
        "level": level,
        "text": text_clean,
        "page": r["page"]
    })

# Final structured JSON
output = {
    "title": title,
    "outline": outline
}

# Create the output directory if it doesn't exist
os.makedirs("output", exist_ok=True)

# Define the output file path
output_path = os.path.join("output", "semantic_output.json")

# Write JSON to file
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"Processing Completed")
