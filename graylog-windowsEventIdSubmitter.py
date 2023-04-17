# ##############################
import requests                #
from datetime import datetime  #
from redminelib import Redmine #
import redminelib              #
import urllib3                 #
import logging                 #
# ##############################

# LOGGING
logging.basicConfig(
    filename=f"graylog-eventID-submitter.log",
    filemode='w',
    format='%(asctime)s : %(levelname)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    encoding="utf-8")

today_date = datetime.now().strftime("%d.%m.%Y")

# I'VE GOT SOME HTTPS PROBLEM SO THAN I DISABLED WITH THIS COMMAND.
urllib3.disable_warnings()

class GraylogEventIDSubmitter:
    def __init__(self):
        # WINDOWS EVENTS DB
        self.windows_events = {
            "4720": {
                "title": "Yeni Kullanıcı Oluşturulması (Event ID: 4720)",
                "desc": "+Bu olay+, yeni bir kullanıcı hesabı *oluşturulduğunda* gözlemlenmektedir.\n",
                "desc_last": "adlı kullanıcı hesabı oluşturulmuştur.\n",
                "events": set(),
                "log": ""
            },
            "4722": {
                "title": "Kullanıcı Hesabının Etkinleştirilmesi (Event ID: 4722)",
                "desc": "+Bu olay+, bir kullanıcı hesabı *etkinleştirildiğinde* gözlemlenmektedir.\n",
                "desc_last": "adlı kullanıcı hesabı etkinleştirilmiştir.\n",
                "events": set(),
                "log": ""
            },
            "4724": {
                "title": "Parola Sıfırlama Denemesi (Event ID: 4724)",
                "desc": "+Bu olay+, bir hesap başka bir hesabın şifresini her *sıfırlamaya* çalıştığında oluşur.\n",
                "desc_last": "adlı kullanıcı hesabı üzerinde parolasını sıfırlama isteğinde bulunmuştur.\n",
                "events": set(),
                "log": ""
            },
            "4725": {
                "title": "Kullanıcı Hesabı Devre Dışı Bırakılması (Event_ID: 4725)",
                "desc": "+Bu olay+, bir kullanıcı hesabı devre dışı bırakıldığında gözlemlenmektedir.\n",
                "desc_last": "adlı kullanıcının hesabı devre dışı bırakılmıştır.\n",
                "events": set(),
                "log": ""
            }
        }

        """
        IF YOU HAVE MORE WINDOWS EVENT'S YOU CAN ADD TO DICT. LIKE..
        "EVENT_ID" : {
            "TITLE": "TITLE"
            ...
        }
        """
    
    def create_ticket(self, event_id):
        TICKET_URL = "<TICKET_URL>"
        events = ""

        for event in self.windows_events[event_id]['events']:
            events += f"{event}\n"

        # COMMON CONTENT CREATED FOR THE TICKET TO BE OPENED. YOU CAN CHANGE..
        description = f"""*Tarih:* {today_date}\n
*Açıklama:*\n
İlgili tarihte *{event_id} ID'e* sahip Windows olayı oluştuğu gözlemlenmiştir.\n
{self.windows_events[event_id]['desc']}
*Yapılan Incelemelerde:*\n
{events}*Tavsiye:*\n
İlgili olayın bilginiz dahilinde olduğunu doğrulamanızı öneririz.\n
*Olaya Ait Örnek Log / Loglar:*\n
<pre>
{self.windows_events[event_id]['log']}
</pre>"""

        redmine = Redmine(TICKET_URL, requests = {"verify": False}, key='<REDMINE_API_KEY>')

        redmine.issue.create(
            project_id = '10',
            subject = self.windows_events[event_id]['title'],
            tracker_id = 8, # CATEGORY OF TYPE ON REDMINE
            description = description,
            status_id = 1,
            priority_id = 2,
            assigned_to_id = 133,
            custom_fields = [{'id': 12, "value": f"Windows\t{event_id}"}]
        )

        """
            IF YOU DON'T KNOW HOW CAN I REQUEST TO TICKET SYSTEM, 
            YOU SHOULD TO -> https://python-redmine.com/configuration.html
        """

        logging.info(f"[+] {event_id} EVENT TICKET IS CREATED.")
    
    def search_event(self):
        USERNAME = "<USERNAME>"
        PASSWORD = "<PASSWORD>"
        GRAYLOG_URL = "<GRAYLOG_URL>"

        for event_id in self.windows_events.items():
            search_query = {
                'query': f"EventID:{event_id[0]}",
                'range': 900000 # 300: 5 MINUTES AGO, 900: 15 MINUTES AGO, 900000: 10 DAYS AGO
            }

            # YOU CAN LOOK > https://go2docs.graylog.org/5-0/setting_up_graylog/rest_api.html

            # REQUEST FOR GRAYLOG
            response = requests.get(
                f"{GRAYLOG_URL}/api/search/universal/relative",
                headers = {"Content-Type": "application/json"},
                auth=(USERNAME, PASSWORD),
                params=search_query,
                verify=False
            )

            # RESULT CODE IS OK ?
            if response.status_code == 200:
                # DATA IS RECEIVED WITH JSON
                for event in response.json()["messages"]:
                    event_log = event["message"]["message"]
                    eventID = event["message"]["EventID"]
                    source_user = event_log.split("Account Name:")[1].split("Account Domain:")[0].strip()
                    destination_user = event_log.split("Account Name:")[2].split("Account Domain:")[0].strip()

                    """
                        THE VALUES HOLDED IN THE ABOVE VARIABLES ARE SOME VALUES 
                        TO BE USED FROM THE LOG CONTAINED IN ALERT ON GRAYLOG.
                    """
                    
                    # IF THE EVENT ID FROM THE LOG AND THE EVENT ID VALUE IN THE WINDOWS EVENT ID LIST EQUAL
                    if event_id[0] == eventID and event_log != "":
                        # ADD TO WINDOWS EVENTS DB
                        self.windows_events[eventID]['events'].add(f"* *{source_user}* adlı kullanıcı tarafından *{destination_user}* {self.windows_events[eventID]['desc_last']}")
                        self.windows_events[eventID]['log'] = event_log

                # IF THERE IS DATA
                if len(self.windows_events[event_id[0]]["events"]) > 0:
                    # CREATE TICKET
                    self.create_ticket(event_id[0])
            else:
                logging.error("[-] ERROR STATUS CODE DIFFERENT FROM 200.")
                break
            
try:
    result = GraylogEventIDSubmitter()
    result.search_event()
except redminelib.exceptions.AuthError:
    logging.error(f"[-] INVALID USERNAME OR PASSWORD") 
    exit()
except KeyboardInterrupt or KeyError:
    logging.error(f"[-] PROGRAM STOPPED BECAUSE CTRL KEY DETECTED.") 
    exit()
except requests.exceptions.ConnectTimeout:
    logging.error(f"[-] SOME CONNECTION PROBLEM..")
    exit()
except requests.exceptions.ConnectionError:
    logging.error(f"[-] CONNECTION FAILD.")
    exit()

# CREATED BY © n3gat1v3o