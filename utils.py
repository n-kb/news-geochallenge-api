# -*- coding: utf-8 -*-

from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import pymongo
from flask_cors import CORS
from bson.objectid import ObjectId
from eventregistry import *
import datetime, time, random, json, os, requests, hashlib
from bson import ObjectId
from datetime import timedelta

EVENTREGISTRY_API_KEY = os.environ["EVENTREGISTRY_API_KEY"]
SALT = os.environ["SALT"]

def geoloc(location):
    url = "https://nominatim.openstreetmap.org/search/?format=json&q=%s&limit=1" % location
    time.sleep(1 + random.random())
    r = requests.get(url)
    data = json.loads(r.text)
    try:
        result = data[0]
        lat = result["lat"]
        lon = result["lon"]
        return lat, lon
    except IndexError:
        # Could not geolocate
        return None, None

def refresh_questions(db):
    inserted_questions = 0
    questions = db.questions
    questions.create_index("uri", unique= True)
    dateStart = datetime.date.today() + datetime.timedelta(days=-30)
    dateEnd = datetime.date.today()
    er = EventRegistry(apiKey = EVENTREGISTRY_API_KEY)
    q = QueryEventsIter(dateStart = dateStart, dateEnd = dateEnd, lang="eng")
    for event in q.execQuery(er, 
                             sortBy = "date", 
                             returnInfo = ReturnInfo( eventInfo = EventInfoFlags(imageCount = 1)), 
                             maxItems = 20, 
                             eventBatchSize = 20):
        if event["location"] is not None and "images" in event:
            location = event["location"]["label"]["eng"] + ", " + event["location"]["country"]["label"]["eng"]
            lat,lon = geoloc(location.replace(" ", ""))
            if lat is not None:
                question = {
                             "img" : event["images"][0],
                             "location": location,
                             "lat": lat,
                             "title": event["title"]["eng"],
                             "lon": lon,
                             "uri": event["uri"],
                             "date": datetime.datetime.strptime(event["eventDate"], "%Y-%m-%d"),
                             "articleCount": event["totalArticleCount"]}
                try:
                    questions.insert(question)
                    inserted_questions += 1
                except pymongo.errors.DuplicateKeyError:
                    continue
    return jsonify({"status": "OK", "inserted_questions": inserted_questions})

def make_token():
    unixtime = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
    unixtime_rounded = int(unixtime / 100) * 100
    return hashlib.md5((SALT + str(unixtime_rounded)).encode("ascii")).hexdigest()

def check_token(token):
    unixtime = (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
    unixtime_rounded = int(unixtime / 100) * 100
    current_token = hashlib.md5((SALT + str(unixtime_rounded)).encode("ascii")).hexdigest()
    previous_token = hashlib.md5((SALT + str(unixtime_rounded - 100)).encode("ascii")).hexdigest()

    if token == current_token or token == previous_token:
        return True
    else:
        return False

def jsonEncode(l):
    returned_dict = {}
    for key, value in l.iteritems():
        if isinstance(value, ObjectId):
            returned_dict[key] = str(value)
        else:
            returned_dict[key] = value
    return returned_dict

def get_questions(db, difficulty):
    minArticleCount = 0
    maxArticleCount = 9999
    dateStart = datetime.datetime.now() + datetime.timedelta(days=-30)
    returned_questions = []
    if difficulty == "easy" or difficulty == "very-easy":
        minArticleCount = 200
    elif difficulty == "medium":
        minArticleCount = 80
        maxArticleCount = 250
    elif difficulty == "hard":
        maxArticleCount = 100
    questions = list(db.questions.find({"articleCount" : {"$lt": maxArticleCount, "$gt": minArticleCount}}).sort("date", pymongo.DESCENDING).limit(30))
    random.shuffle(questions) 
    q_count = 0
    for question in questions:
        if q_count < 2:
            returned_questions.append(jsonEncode(question))
            q_count += 1

    return jsonify({"token": make_token(), "questions": returned_questions})

def make_username():
    animals = ["fox 🦊", "gorilla 🦍", "cat 🐱", "dog 🐶", "wolf 🐺"]
    return "Anonymous " + animals[int(random.random() * len(animals))]

def add_score(db, points, token):
    if check_token(token):
        scores = db.scores
        username = make_username()
        score_id = scores.insert({"score": points, "username": username, "date": datetime.datetime.utcnow().strftime("%Y%m%d")})
        position_today = scores.find({"date": datetime.datetime.utcnow().strftime("%Y%m%d"), "score": {"$gte": points}}).count()
        position_alltime = scores.find({"score": {"$gte": points}}).count()

        return jsonify({"score_id": str(score_id), "position_alltime": position_alltime, "position_today": position_today})
    else:
        return jsonify({"error": "Could not insert score"})

def change_username(db, score_id, username):
    if len(username) > 0:
        forbidden_chars = set('$(){}/\'",;')
        username_clean = ''.join([c for c in username if c not in forbidden_chars])
        scores = db.scores
        scores.update_one({
                          '_id': ObjectId(score_id)
                        },{
                          '$set': {
                            'username': username_clean
                          }
                        }, upsert=False)
        return jsonify({"status": "OK"})
    return jsonify({"status": "error"})

def get_scores(db):
    returned = {"scores_alltime": [], "scores_today": []}
    scores = db.scores
    scores_alltime = list(scores.find().sort("score", pymongo.DESCENDING).limit(10))
    for score_alltime in scores_alltime:
        returned["scores_alltime"].append(jsonEncode(score_alltime))
    scores_today = list(scores.find({"date": datetime.datetime.utcnow().strftime("%Y%m%d") }).sort("score", pymongo.DESCENDING).limit(10))
    for score_today in scores_today:
        returned["scores_today"].append(jsonEncode(score_today))

    return jsonify(returned)