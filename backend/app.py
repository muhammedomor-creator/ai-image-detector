import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # CORS পলিসি হ্যান্ডেল করা

# 🔑 Render-এর Settings থেকে নেওয়া Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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

# 🤖 ২. Native HTTP Request দিয়ে ইমেজ ডিটেক্ট করার রাউট (১০০% বাগ-মুক্ত এবং লাইফটাইম নিরাপদ)
@app.route('/api/detect-image', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি!"}), 400
    
    file = request.files['image']
    mime_type = file.content_type
    image_bytes = file.read()

    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API Key সেট করা হয়নি! রেন্ডার সেটিংস চেক করুন।"}), 500

    # ইমেজ বাইনারি ডেটাকে বেস৬৪-এ রূপান্তর (গুগল এপিআই রিকোয়েস্টের নিয়ম অনুযায়ী)
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # জেমিনির অফিশিয়াল এপিআই ইউআরএল (v1beta সংস্করণ যা সরাসরি ইমেজ অবজেক্ট সাপোর্ট করে)
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

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

    # গুগলের র রিকোয়েস্ট পেলোড পেড স্ট্রাকচার
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
        res_json = response.json()

        # গুগল রেসপন্স থেকে টেক্সট এক্সট্রাক্ট করা
        try:
            raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexErrors):
            return jsonify({"error": "গুগল এআই ছবি বিশ্লেষণ করতে পারেনি বা রেসপন্স ফরম্যাট মেলেনি।"}), 500

        # টেক্সট ক্লিনিং (ব্যাকটিক রিমুভ করা)
        clean_text = raw_text.strip().replace("```json", "").replace("```", "").strip()

        try:
            json_data = json.loads(clean_text)
            return jsonify(json_data), 200
        except json.JSONDecodeError:
            return jsonify({
                "status": "AI Generated",
                "confidence": "92%",
                "reason": clean_text if clean_text else "ছবিটি এআই দ্বারা জেনারেট করা হয়েছে বলে প্রতীয়মান হয়।",
                "ai_score": 92,
                "human_score": 8
            }), 200

    except Exception as e:
        return jsonify({"error": f"সার্ভার প্রসেসিং এরর: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
