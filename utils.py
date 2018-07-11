# -*- coding: utf-8 -*-

from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
import pymongo
from flask_cors import CORS
from bson.objectid import ObjectId
import datetime, time, random, json, os, requests, hashlib
from bson import ObjectId
from datetime import timedelta

SALT = os.environ["SALT"]

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