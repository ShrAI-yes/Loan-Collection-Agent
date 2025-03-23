import firebase_admin
from firebase_admin import credentials, firestore
from langchain.chains.question_answering.map_reduce_prompt import messages


class Database:
    def __init__(self):
        #Check Credentials JSON File path
        self.cred = credentials.Certificate("./predixion-145c5-firebase-adminsdk-fbsvc-e0abad91cf.json")
        firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()

    def init_user(self,phone: str, wa_id=None, chat_id=None, name=None):
        doc_ref = self.db.collection("testing").document(phone)
        if not doc_ref.get().exists:
            data = {
                "whatsApp_id": wa_id,
                "id": chat_id,
                "phone": phone,
                "name": name,
                "messages": [],
            }
            self.db.collection("testing").document(phone).set(data)

        return self.db.collection("testing").document(phone)

    def payload(self, name: str, text, time):
        msg = {
            f"{name}": str(text),
            "timestamp": time
        }
        return msg

    def add_convo(self, ref, msg):
        ref.update({"messages": firestore.ArrayUnion([msg])})

    def get_convo(self, ref):
        conversation = ref.get().to_dict()['messages']

        for msg in conversation:
            if 'timestamp' in msg:
                del msg['timestamp']

        return conversation