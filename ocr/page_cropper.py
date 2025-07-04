def crop_10x3_grid(page_img):
    """
    Given a full-page OpenCV image, return a list of cropped 10x3 entry boxes.
    """
    h, w, _ = page_img.shape

    top_offset = int(h * 0.03)
    bottom_offset = int(h * 0.026)
    usable_height = h - top_offset - bottom_offset
    side_offset = int(w * 0.02)
    usable_width = w - 2 * side_offset

    box_h = usable_height // 10
    box_w = usable_width // 3

    boxes = []
    for row in range(10):
        for col in range(3):
            y1 = top_offset + row * box_h
            y2 = y1 + box_h
            x1 = side_offset + col * box_w
            x2 = x1 + box_w
            boxes.append({
                "row": row + 1,
                "col": col + 1,
                "image": page_img[y1:y2, x1:x2]
            })
    return boxes
