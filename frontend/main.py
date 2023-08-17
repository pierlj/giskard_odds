import os
import sys
import json
from flask import Flask, render_template, request, url_for, flash, redirect, g, session
from werkzeug.utils import secure_filename

sys.path.insert(1, 'backend/')
print(os.path.abspath('../'))

from odd_computation import compute_odds
from utils import load_empire_dict, setup_upload_folder, allowed_file, GRAPH_SAVE_PATH


UPLOAD_FOLDER = 'frontend/static/uploads'
MILLENIUM_PATH = 'frontend/static/ressources/millennium-falcon.json'


app = Flask(__name__)
app.config['SECRET_KEY'] = '827491775492f30454eede9bd3d2614f330f2d1551d0cda5'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/")
def home():
    if "odds_dict" in session:
        odds_dict = session["odds_dict"]
        del session["odds_dict"]
        return render_template("home.html", messages=odds_dict)
    return render_template("home.html", messages={"visibility": "hidden"})


@app.route('/', methods=['GET', 'POST'])
def upload_json():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for("home"))
    file = request.files['file']

    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(url_for("home"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        setup_upload_folder(app.config['UPLOAD_FOLDER'])

        empire_file_path = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename)
        file.save(empire_file_path)
        empire_dict = load_empire_dict(empire_file_path)
        if empire_dict is not None:
            flash('Successfully loaded JSON Empire file: {}.'.format(empire_file_path))
            redirect(url_for("home"))
            odds, itinerary = compute_odds(MILLENIUM_PATH, empire_file_path)
            
            odds_dict = {"odds": odds,
                        "itinerary": itinerary if itinerary is not None else ["It is not possible to reach the planet in time."],
                        "empire_dict": empire_dict,
                        "visibility": "visible",
                        "routes_img": GRAPH_SAVE_PATH.split('static')[1] if os.path.isfile(GRAPH_SAVE_PATH) else ''}
            session["odds_dict"] = odds_dict
            return redirect(url_for("home"))
        else: 
            flash('Error loading JSON Empire file, please try with a proper Empire file.')
        return redirect(url_for("home"))
    else:
        flash('Only JSON files are allowed.')
        return redirect(url_for("home"))


if __name__ == '__main__':
    app.run()