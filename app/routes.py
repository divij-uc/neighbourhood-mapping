from app import app, db
from app.models import Neighborhood, Location, Respondent, Feedback
from app.forms import SurveyStart, SurveyDraw, AgreeButton, SurveyDemo, SurveyFeedback, validator_geo_json
from flask import render_template, redirect, url_for, session, flash
from wtforms.validators import DataRequired
from utils import get_geojson, get_map_comps, get_neighborhood_list
from datetime import datetime, timezone
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
import uuid

neighborhood_list = get_neighborhood_list()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def start_page():
    agree = AgreeButton()
    if agree.validate_on_submit():
        session["uuid"] = str(uuid.uuid4())
        location = Location(
            user_id=session["uuid"], time_stamp=datetime.now(timezone.utc)
        )
        db.session.add(location)
        db.session.commit()
        return redirect(url_for("survey_form"))
    return render_template("start_page.html", agree=agree)


@app.route("/survey_form", methods=["GET", "POST"])
def survey_form():
    draw_options = {
        "polygon": False,
        "polyline": False,
        "rectangle": False,
        "circle": False,
        "marker": False,
        "circlemarker": {"radius": 20},
    }
    header, body_html, script = get_map_comps(
        loc=(41.8781, -87.6298), zoom=12, draw_options=draw_options
    )
    form = SurveyStart()

    if form.validate_on_submit():
        parsed_geojson = get_geojson(form.mark_layer.data)
        location = Location.query.filter_by(user_id=session["uuid"]).first()
        location.geometry = from_shape(shape(parsed_geojson["features"][0]["geometry"]))
        # location.name = form.cur_neighborhood.data
        # location.rent_own = form.rent_own.data
        # location.years_lived = form.years_lived.data
        location.time_stamp = datetime.now(timezone.utc)
        db.session.commit()
        return redirect(url_for("survey_draw", first="first"))

    return render_template(
        "form_page_start.html",
        form=form,
        neighborhood_list=neighborhood_list,
        header=header,
        body_html=body_html,
        script=script,
    )


@app.route("/survey_draw/<first>", methods=["GET", "POST"])
def survey_draw(first):
    draw_options = {
        "polyline": False,
        "rectangle": False,
        "circle": False,
        "marker": False,
        "circlemarker": False,
    }
    if first == "first":
        location = Location.query.filter_by(user_id=session["uuid"]).first()
        pt = to_shape(location.geometry)
        loc = pt.y, pt.x
    else:
        loc = (41.8781, -87.6298)
    header, body_html, script = get_map_comps(
        loc=loc, zoom=13, draw_options=draw_options
    )
    form = SurveyDraw()
    if form.validate_on_submit():
        parsed_geojson = get_geojson(form.draw_layer.data)
        try:
            geometry = from_shape(shape(parsed_geojson["features"][0]["geometry"]))
        except:
            geometry = None
        neighborhood = Neighborhood(
            user_id=session["uuid"],
            geometry=geometry,
            time_stamp=datetime.now(timezone.utc),
            name=form.cur_neighborhood.data
        )
        if first == "first":
            neighborhood.user_relationship = ["cur_live"]
            # neighborhood.name = location.name
        else:
            neighborhood.user_relationship = form.user_relationship.data
            # neighborhood.name = form.cur_neighborhood.data
        db.session.add(neighborhood)
        db.session.commit()
        if form.submit.data:
            return redirect(url_for("survey_demo"))
        elif form.draw_another.data:
            return redirect(url_for("survey_draw", first="next"))
    # if first == "first":
    #     form.cur_neighborhood.data = location.name
    # else:
    # form.cur_neighborhood.data = ""
    return render_template(
        "form_page_draw.html",
        form=form,
        header=header,
        body_html=body_html,
        script=script,
        first=first,
        neighborhood_list=neighborhood_list,
    )


@app.route("/survey_demo", methods=["GET", "POST"])
def survey_demo():
    form = SurveyDemo()
    if form.validate_on_submit():
        resp = Respondent(
            user_id=session["uuid"],
            rent_own=form.rent_own.data,
            years_lived_chicago=form.years_lived_chicago.data,
            years_lived=form.years_lived.data,
            age=form.age.data,
            gender=form.gender.data,
            ethnicity=form.ethnicity.data,
            soc_cohes_neighborhood_knit=form.soc_cohes_neighborhood_knit.data,
            soc_cohes_neighborhood_value=form.soc_cohes_neighborhood_value.data,
            soc_cohes_neighborhood_talk=form.soc_cohes_neighborhood_talk.data,
            soc_cohes_neighborhood_belong=form.soc_cohes_neighborhood_belong.data,
        )
        db.session.add(resp)
        db.session.commit()
        return redirect(url_for("thank_page", feedback_page="feedback"))

    return render_template("form_page_demo.html", form=form)


@app.route("/thank_you/<feedback_page>", methods=["GET", "POST"])
def thank_page(feedback_page):
    form = SurveyFeedback()
    if form.validate_on_submit():
        feedback = Feedback(
            user_id=session["uuid"], feedback=form.feedback.data, email=form.email.data
        )
        db.session.add(feedback)
        db.session.commit()
        return redirect(url_for("thank_page", feedback_page="thank_you"))
    return render_template("thank_page.html", form=form, feedback_page=feedback_page)
