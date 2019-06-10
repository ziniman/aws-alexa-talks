import boto3
import json
import logging
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from datetime import datetime, timedelta
from dateutil import tz
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('boaz_sessions')

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def get_session():
    filename = 'sessions_list'
    cache = read_cache(filename)
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz('Asia/Jerusalem')

    timestamp = datetime.utcnow()
    timestamp = timestamp.replace(tzinfo=from_zone)
    timestamp = timestamp.astimezone(to_zone)
    timestamp = timestamp.strftime('%Y-%m-%d %H:%M')
    print timestamp

    if not cache:
        try:
            response = table.query(
                IndexName='speaker-datetime-index',
                Limit=1,
                KeyConditionExpression=Key('speaker').eq('Boaz Ziniman') & Key('datetime').gte(timestamp)
            )

            items = response[u'Items']

            buttons = []

            if items:
                for item in items:
                    buttons.append(item)
            else:
                return None

            store_cache(filename, buttons)
            return buttons

        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return None
    else:
        return cache

def store_cache(filename, data):
    file = open('/tmp/%s' % filename,'w')
    json.dump(data, file, cls=DecimalEncoder)
    file.close()

    logger.info('Wrote cache to %s: %s' % (filename, data))
    return True

def read_cache(filename):
    #return False

    try:
        with open('/tmp/%s' % filename) as json_data:
            data = json.load(json_data)
            print(data)
            json_data.close()

        logger.info('Read cache from file %s: %s' % (filename, data))
        return data

    except Exception as e:
        logger.warning("Failed to read cache file %s. %s" % (filename, e))

def alexa_response(content, display_title, display_content, end_session = True):
    logger.info('Responding with: ' + content)
    if not (display_content): display_content = content
    return {
        'version': '1.0',
        'sessionAttributes': {},
        'response': {
          'outputSpeech': {
            'type': 'PlainText',
            'text': content
          },
          'card': {
            'type': 'Simple',
            'title': display_title,
            'content': display_content
          },
          "reprompt": {
              "outputSpeech": {
                  "type": "PlainText",
                  "text": "Hope to see you there!"
              }
          },
          'shouldEndSession': end_session
        }
    }

def NextSession(event, context):
    #return event
    logger.info('Received event: ' + json.dumps(event))

    if event['request']['type'] == "LaunchRequest":
        content = "Thanks for Using this Skill. You can ask for the next session."
        logger.info('Responding with: ' + content)
        return alexa_response(content, 'Welcome', content, False)
    elif event['request']['type'] == "SessionEndedRequest":
        content = "Hummm... See you soon";
        return alexa_response(content, 'Goodbye', content)
    else:
        intent = event['request']['intent']['name']

    interfaces = event['context']['System']['device']['supportedInterfaces']

    #if interfaces['Display']:
        #display_template = interfaces['Display']['templateVersion']
        #display_markup = interfaces['Display']['markupVersion']

    #logger.info('Dispaly Template: ' + display_template)
    #logger.info('Markup Version: ' + display_markup)

    if (intent=='GetNextTalk'):
        lookup_val = time.strftime("%d-%m-%Y")

        #if intent == 'GetNextTalk':

        #TZ Adjustments - Basic TZ is UTC
        current_ts = int(time.time()) + (60*60*3)

        next_session = get_session()
        logger.info(next_session)
        item = None

        if next_session:
            for item in next_session:
                speaker = item['speaker']
                session_name = item['topic']
                session_date = item['datetime']
                session_location = item['location']

        if item:
            logger.info(item)
            session_short_date = datetime.strptime(session_date,'%Y-%m-%d %H:%M').strftime('%b %d, %Y, %H:%M')
            session_date = datetime.strptime(session_date,'%Y-%m-%d %H:%M').strftime('%B %d at %H:%M')
            content = 'Next session for %s is.  %s, on %s, in %s' % (speaker, session_name, session_date, session_location)
            display_content = '%s\n%s\n%s' % (session_name, session_short_date, session_location)
            display_title = '%s\'s Next Session' % (speaker)
        else:
            content = 'I could not find any future sessions.'
        return alexa_response(content, display_title, display_content)
    elif (intent=='GetSpecificRange'):
        content = 'This functionality is not available yet. Check out the next version. You can ask for the next session'
        return alexa_response(content, 'Under Constraction', content, False)
    else:
        if (intent=='AMAZON.HelpIntent'):
            content = 'This skill can provide information regarding the next session of Boaz Ziniman - A Technical Evangelist from AWS Tel Aviv'
            display_content = 'This skill can provide information regarding the next session of Boaz Ziniman - A Technical Evangelist from AWS Tel Aviv'
            display_title = 'Need some help?'
            return alexa_response(content, display_title, display_content, False)
        else:
            content = 'Leaving so early? See you next time.'
            display_content = 'Leaving so early?\nSee you next time.'
            display_title = ':-('
            return alexa_response(content, display_title, display_content)
