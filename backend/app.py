import os
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # ফ্রন্টএন্ড থেকে রিকোয়েস্ট আসার অনুমতি বা CORS পলিসি হ্যান্ডেল করা

# 🔑 Render-এর Environment Variable থেকে নিরাপদ উপায়ে Gemini API Key নেওয়া
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 🇧🇩 বাংলাদেশি ফোন নম্বর সঠিক ফরম্যাটে (+880) রূপান্তর করার ফাংশন
def format_bd_number(phone):
    cleaned = ''.join(filter(str.isdigit, phone)) # টেক্সট থেকে শুধু সংখ্যাগুলো আলাদা করা
    if cleaned.startswith('01') and len(cleaned) == 11:
        return "88" + cleaned
    elif cleaned.startswith('8801') and len(cleaned) == 13:
        return cleaned
    return cleaned

# 💬 ১. হোয়াটসঅ্যাপ ওটিপি পাঠানোর এপিআই রাউট (WhatsApp OTP Route)
@app.route('/api/send-whatsapp-otp', methods=['POST'])
def send_whatsapp_otp():
    data = request.json
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
        }, headers={"Content-Type": "application/json"})
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": "হোয়াটসঅ্যাপ এপিআই কানেকশনে সমস্যা: " + str(e)}), 500

# 🤖 ২. Gemini API দিয়ে ছবি আসল নাকি এআই দিয়ে তৈরি তা ডিটেক্ট করার রাউট
@app.route('/api/detect-image', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি!"}), 400
    
    file = request.files['image']
    image_bytes = file.read()

    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API Key সেট করা হয়নি! রেন্ডার সেটিংস চেক করুন।"}), 500

    # ছবির জন্য সবচেয়ে দ্রুত এবং শক্তিশালী মডেল Gemini 1.5 Flash
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # এআই-কে নিখুঁত ও নির্দিষ্ট ফরম্যাটে উত্তর দেওয়ার জন্য প্রম্পট
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
        # জেমিনি সার্ভারে ছবি এবং প্রম্পট পাঠিয়ে বিশ্লেষণ করা
        response = model.generate_content([
            prompt,
            {"mime_type": file.content_type, "data": image_bytes}
        ])
        
        # জেমিনির টেক্সট রেসপন্স থেকে যদি কোনো অতিরিক্ত ব্যাকটিক বা জেসন ট্যাগ থাকে তা ক্লিন করা
        clean_text = response.text.strip().replace("```json", "").replace("```", "")
        return clean_text, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        return jsonify({"error": f"Gemini API তে সমস্যা হয়েছে: {str(e)}"}), 500

if __name__ == '__main__':
    # রেন্ডার ডট কমের পোর্ট ম্যানেজমেন্ট
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
