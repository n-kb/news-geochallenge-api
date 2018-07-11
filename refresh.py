from pymongo import MongoClient
import os, datetime, random, time
import pymongo
import utils
from eventregistry import *

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

if __name__ == '__main__':

    EVENTREGISTRY_API_KEY = os.environ["EVENTREGISTRY_API_KEY"]

    if (os.environ.get('MONGODB_URI')):
        db_name = os.environ.get('MONGODB_URI').split("/")[3]
        db_uri = os.environ.get('MONGODB_URI')
    else:
        db_name = 'geochallenge'
        db_uri = 'mongodb://localhost:27017/geochallenge'

    db = MongoClient(db_uri)[db_name]

    inserted_questions = 0
    questions = db.questions
    questions.create_index("uri", unique= True)
    dateStart = datetime.date.today() + datetime.timedelta(days=-30)
    dateEnd = datetime.date.today()
    er = EventRegistry(apiKey = EVENTREGISTRY_API_KEY)
    q = QueryEventsIter(dateStart = dateStart, dateEnd = dateEnd, lang="eng", minArticlesInEvent=200)
    for event in q.execQuery(er, 
                             sortBy = "date", 
                             returnInfo = ReturnInfo( eventInfo = EventInfoFlags(imageCount = 1)), 
                             maxItems = 50, 
                             eventBatchSize = 50):
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
    print ({"status": "OK", "inserted_questions": inserted_questions})