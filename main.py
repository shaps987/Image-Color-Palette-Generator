from flask import Flask, request, render_template, redirect, url_for
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'

# Configure the upload folder (inside static/)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
 
def get_top_10_hex_colors(image_path, css_colors_json="css_colors.json"):
    """
    Load an image, read CSS colors from a JSON file, cluster each unique (R,G,B)
    to the closest CSS3 color by Euclidean distance, and return a dict of the
    top 10 color names -> single representative hex code.
    """
    import json
    import numpy as np
    from PIL import Image
    from collections import defaultdict
    import webcolors

    # 1) Read CSS color mapping from a JSON file
    with open(css_colors_json, "r") as f:
        css_names_to_hex = json.load(f)

    # 2) Invert to get {'#rrggbb': 'colorname'}
    css_hex_to_names = {val.lower(): key for key, val in css_names_to_hex.items()}

    # 3) Helper function
    def closest_css3_name(rgb_tuple):
        (r, g, b) = rgb_tuple
        min_dist_sq = float("inf")
        best_name = None
        for hex_code, color_name in css_hex_to_names.items():
            (rh, gh, bh) = webcolors.hex_to_rgb(hex_code)
            dist_sq = (r - rh)**2 + (g - gh)**2 + (b - bh)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_name = color_name
        return best_name

    # 4) Open the image
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    pixels = arr.reshape(-1, 3)

    # 5) Unique colors & frequency
    unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)

    # 6) Group by approximate CSS name
    from collections import defaultdict
    css_groups = defaultdict(list)
    css_group_counts = defaultdict(int)

    for rgb_arr, freq in zip(unique_colors, counts):
        rgb_tuple = tuple(rgb_arr)
        color_name = closest_css3_name(rgb_tuple)
        hex_code = webcolors.rgb_to_hex(rgb_tuple).lower()
        css_groups[color_name].append((hex_code, freq))
        css_group_counts[color_name] += freq

    # 7) Sort by total frequency, pick top 10
    sorted_names = sorted(css_group_counts, key=css_group_counts.get, reverse=True)
    top_10_names = sorted_names[:10]

    # 8) Within each group, pick the single most frequent hex
    final_dict = {}
    for color_name in top_10_names:
        subcolors = css_groups[color_name]
        best_hex_code, _ = max(subcolors, key=lambda x: x[1])
        final_dict[color_name] = best_hex_code

    return final_dict

@app.route('/', methods=['GET'])
def index():
    # Display the upload page by default
    return render_template('index.html', filename=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload from the form.
    """
    if 'file' not in request.files:
        return redirect(url_for('index'))  # No file in form

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))  # User submitted an empty file

    if file:
        filename = file.filename
        # Save to static/uploads/...
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # Generate top 10 colors
        top_10_dict = get_top_10_hex_colors(save_path, css_colors_json="colors.json")
        print(top_10_dict)

        # Render the page with the uploaded filename & color results
        return render_template('index.html',
                               filename=filename,
                               save_path=save_path,
                               top_10_dict=top_10_dict)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)