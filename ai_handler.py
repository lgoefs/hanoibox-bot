import anthropic, os, base64, json
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

class AIHandler:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5-20251001"

    def interpret_message(self, text, context):
        system = f"""You are HanoiBox gym assistant in Hanoi, Vietnam.
Gym context: {json.dumps(context)}
Commands available: 'check in [name]', 'new member', 'log payment', 'members', 'expiring', 'summary'
Respond concisely. If they are trying to do something, tell them the exact command."""
        r = self.client.messages.create(model=self.model, max_tokens=300,
            system=system, messages=[{"role":"user","content":text}])
        return r.content[0].text

    def read_payment_receipt(self, image_bytes, mime="image/jpeg"):
        img = base64.standard_b64encode(image_bytes).decode()
        r = self.client.messages.create(model=self.model, max_tokens=400,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":mime,"data":img}},
                {"type":"text","text":"""Extract from this payment receipt and return JSON only:
{"member_name":null,"amount_vnd":null,"method":null,"plan":null,"notes":""}"""}]}])
        try: return json.loads(r.content[0].text.strip())
        except: return {"notes": r.content[0].text}

    def read_member_id(self, image_bytes, mime="image/jpeg"):
        img = base64.standard_b64encode(image_bytes).decode()
        r = self.client.messages.create(model=self.model, max_tokens=300,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":mime,"data":img}},
                {"type":"text","text":"Extract contact info from this image. Return JSON only: {\"name\":null,\"phone\":null,\"email\":null}"}]}])
        try: return json.loads(r.content[0].text.strip())
        except: return {"notes": r.content[0].text}

    def generate_daily_summary(self, data):
        r = self.client.messages.create(model=self.model, max_tokens=400,
            messages=[{"role":"user","content":f"Write a brief gym daily summary with emojis. Data: {json.dumps(data)}. Under 150 words. Flag anything needing attention."}])
        return r.content[0].text
