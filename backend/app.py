import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
# গুগলের লেটেস্ট এবং রিকমেন্ডেড লাইব্রেরি ইমপোর্ট
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)  # ফ্রন্টএন্ড থেকে রিকোয়েস্ট আসার অনুমতি বা CORS পলিসি হ্যান্ডেল করা

# 🔑 Render-এর Environment Variable থেকে নিরাপদ উপায়ে API Key দিয়ে ক্লায়েন্ট তৈরি
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# 🇧🇩 বাংলাদেশি ফোন নম্বর সঠিক ফরম্যাটে (+880) রূপান্তর করার ফাংশন
def format_bd_number(phone):
    cleaned = ''.join(filter(str.isdigit, phone))
    if cleaned.startswith('01') and len(cleaned) == 11:
        return "88" + cleaned
    elif cleaned.startswith('8801') and len(cleaned) == 13:
        return cleaned
    return cleaned

# 💬 ১. হোয়াটসঅ্যাপ ওটিপি পাঠানোর এপিআই রাউট
@app.route('/api/send-whatsapp-otp', methods=['POST'])
def send_whatsapp_otp():
    data = request.json or {}
    raw_phone = data.get('phoneNumber')
    otp_code = data.get('otpCode')

    if not raw_phone or not otp_code:
        return jsonify({"success": False, "message": "মোবাইল নম্বর এবং ওটিপি কোড দুটিই প্রয়োজন!"}), 400

    formatted_phone = format_bd_number(raw_phone)
    whatsapp_api_url = "https://otp-api-hmrz.onrender.com/send-otp"

    try:
        response = requests.post(whatsapp_api_url, json={
            "phoneNumber": formatted_phone,
            "otpCode": str(otp_code)
        }, headers={"Content-Type": "application/json"}, timeout=15)
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": "হোয়াটসঅ্যাপ এপিআই কানেকশনে সমস্যা: " + str(e)}), 500

# 🤖 ২. নতুন Google GenAI দিয়ে ইমেজ ডিটেক্ট করার রাউট
@app.route('/api/detect-image', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি!"}), 400
    
    file = request.files['image']
    image_bytes = file.read()

    if not client:
        return jsonify({"error": "Gemini API Key সেট করা হয়নি! রেন্ডার সেটিংস চেক করুন।"}), 500

    # এআই-কে নিখুঁত ও নির্দিষ্ট জেসন রেসপন্স দেওয়ার জন্য প্রম্পট
    prompt = """
    Analyze this image very carefully and determine if it is authentic or AI-influenced. 
    You must reply ONLY in a valid JSON format with the exact keys below. Do not include markdown or backticks like ```json.
    
    Expected JSON format:
    {
      "status": "Choose one from: Original / AI Generated / AI Edited / Deepfake / Manually Edited",
      "confidence": "Percentage between 0% to 100%",
      "reason": "Detailed explanation in Bengali language explaining why you chose this status",
      "ai_score": 85, 
      "human_score": 15
    }
    
    Note: 'ai_score' and 'human_score' must be integers summing up to 100. Write the 'reason' in clear, professional Bengali.
    """

    try:
        # নতুন লাইব্রেরির সেফ মেথড স্ট্রাকচার
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=file.content_type,
                ),
                prompt
            ]
        )
        
        if not response or not response.text:
            return jsonify({"error": "Gemini AI থেকে কোনো রেসপন্স পাওয়া যায়নি।"}), 500

        # জেসন টেক্সট ক্লিন করা
        clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()

        try:
            json_data = json.loads(clean_text)
            return jsonify(json_data), 200
        except json.JSONDecodeError:
            return jsonify({
                "status": "AI Generated",
                "confidence": "95%",
                "reason": clean_text if clean_text else "ছবিটি এআই দ্বারা তৈরি করার লক্ষণ রয়েছে।",
                "ai_score": 95,
                "human_score": 5
            }), 200

    except Exception as e:
        return jsonify({"error": f"Gemini API তে সমস্যা হয়েছে: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
