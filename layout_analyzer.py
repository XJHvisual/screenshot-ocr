# -*- coding: utf-8 -*-
"""
Screenshot layout analyzer - separates text regions from image regions.

Uses OCR bounding boxes to create a text mask, then finds connected
components of non-text areas to identify embedded images.
"""

import os
import numpy as np


def extract_image_regions(image_path, ocr_results, min_region_pct=0.015):
    """
    Extract non-text image regions from a screenshot using OCR results.

    Args:
        image_path: Path to the original image
        ocr_results: OCR results as list of [box, text, confidence]
                     where box is [[x1,y1],[x2,y2],[x3,y4],[x4,y4]]
        min_region_pct: Minimum region size as fraction of image area (default 1.5%)

    Returns:
        list of dict: [{path, x, y, w, h}, ...] sorted by vertical position
    """
    try:
        import cv2
    except ImportError:
        raise ImportError(
            "opencv-python is required for image-text separation.\n"
            "Install it with: pip install opencv-python"
        )
    from PIL import Image

    img_cv = cv2.imread(image_path)
    if img_cv is None:
        return []

    h, w = img_cv.shape[:2]
    min_area = int(w * h * min_region_pct)

    # Create text mask from OCR boxes
    mask = np.zeros((h, w), dtype=np.uint8)
    has_boxes = False
    for result in ocr_results:
        if len(result) >= 1 and result[0] is not None:
            box = result[0]
            try:
                pts = np.array(box, dtype=np.int32)
                if pts.ndim == 2:
                    pts = pts.reshape(-1, 1, 2)  # (4,2) -> (4,1,2) for fillPoly
                pts[:, :, 0] = np.clip(pts[:, :, 0], 0, w - 1)
                pts[:, :, 1] = np.clip(pts[:, :, 1], 0, h - 1)
                cv2.fillPoly(mask, [pts], 255)
                has_boxes = True
            except Exception:
                continue

    if not has_boxes:
        return []

    # Dilate to cover text area padding and spacing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (8, 5))
    mask = cv2.dilate(mask, kernel, iterations=2)

    # Additional horizontal dilation to merge nearby words into paragraph blocks
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
    mask = cv2.dilate(mask, h_kernel, iterations=2)

    # Invert to get non-text regions
    non_text_mask = cv2.bitwise_not(mask)

    # Remove thin border margins (window chrome)
    margin = 5
    non_text_mask[:margin, :] = 0
    non_text_mask[-margin:, :] = 0
    non_text_mask[:, :margin] = 0
    non_text_mask[:, -margin:] = 0

    # Find connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        non_text_mask, connectivity=8
    )

    # Extract image regions
    pil_img = Image.open(image_path)
    base = os.path.splitext(image_path)[0]
    regions = []

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]

        # Skip extreme aspect ratios (thin lines/separators)
        aspect = max(bw, bh) / (min(bw, bh) + 1)
        if aspect > 10:
            continue

        # Skip very uniform regions (solid color backgrounds)
        region_cv = img_cv[y:y + bh, x:x + bw]
        if region_cv.size > 0:
            std = float(np.std(region_cv))
            if std < 12:
                continue

        # Crop and save image region
        crop = pil_img.crop((x, y, x + bw, y + bh))
        region_path = f"{base}_img{len(regions)}.png"
        crop.save(region_path, "PNG")

        regions.append({
            "path": region_path,
            "x": x, "y": y, "w": bw, "h": bh,
        })

    # Sort by vertical position (top to bottom)
    regions.sort(key=lambda r: r["y"])

    return regions