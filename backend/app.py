import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageChops
import io

app = Flask(__name__)
CORS(app)

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

# 📸 ২. সরাসরি কোডের মাধ্যমে ইমেজ অ্যানালাইসিস (No Gemini API)
@app.route('/api/detect-image', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি!"}), 400
    
    file = request.files['image']
    image_bytes = file.read()

    try:
        # ছবিটিকে মেমোরিতে ওপেন করা
        img = Image.open(io.BytesIO(image_bytes))
        
        is_edited = False
        software_used = "Unknown"
        reason_list = []
        
        # ১. মেটাডাটা বা এক্সিফ ডাটা (EXIF) চেক করা
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        
        if exif_data:
            for tag, value in exif_data.items():
                # লজিক: মেটাডাটায় যদি কোনো এডিটিং সফটওয়্যার বা এআই ট্যাগ থাকে
                val_str = str(value).lower()
                if 'photoshop' in val_str or 'illustrator' in val_str or 'gimp' in val_str:
                    is_edited = True
                    software_used = "Adobe Photoshop / Editing Suite"
                    reason_list.append("ছবির মেটাডাটায় ডিজিটাল এডিটিং সফটওয়্যারের স্বাক্ষর পাওয়া গেছে।")
                if 'midjourney' in val_str or 'stable diffusion' in val_str or 'dall-e' in val_str:
                    is_edited = True
                    software_used = "AI Generation Tool"
                    reason_list.append("ছবির ইন্টারনাল ট্যাগে এআই জেনারেটরের নাম পাওয়া গেছে।")
        else:
            # সাধারণত এআই জেনারেটেড বা সোশ্যাল মিডিয়া থেকে নামানো এডিটেড ছবির মেটাডাটা বা ক্যামেরা ইনফো থাকে না
            reason_list.append("ছবিটিতে কোনো ক্যামেরা বা ডিভাইসের মেটাডাটা (EXIF) পাওয়া যায়নি, যা এডিটেড বা এআই ছবির ক্ষেত্রে সাধারণ লক্ষণ।")

        # ২. এরর লেভেল অ্যানালাইসিস (ELA) - ডিজিটাল রিসেভিং চেক করা
        # ছবিটিকে একবার ৯০% কোয়ালিটিতে সেভ করে আবার রি-ওপেন করা হয় কম্প্রেশন গ্যাপ বোঝার জন্য
        resaved_stream = io.BytesIO()
        img.convert("RGB").save(resaved_stream, "JPEG", quality=90)
        resaved_stream.seek(0)
        resaved_img = Image.open(resaved_stream)
        
        # দুই ছবির পিক্সেল গ্যাপ বের করা
        diff = ImageChops.difference(img.convert("RGB"), resaved_img)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        # যদি পিক্সেল ডিফারেন্স অনেক বেশি হয়, তার মানে এটি এডিটেড বা এআই ইমেজ
        if max_diff > 35:
            is_edited = True
            reason_list.append(f"ছবির পিক্সেল কম্প্রেশন অ্যানালাইসিসে অসঙ্গতি পাওয়া গেছে (Error Level: {max_diff}), যা রি-সেভ বা এডিটিং নির্দেশ করে।")

        # চূড়ান্ত স্ট্যাটাস ও স্কোর নির্ধারণ
        if is_edited:
            status = "AI Edited / Manually Edited" if software_used != "AI Generation Tool" else "AI Generated"
            ai_score = int(min(max_diff * 2, 95)) if max_diff > 0 else 75
            human_score = 100 - ai_score
            confidence = f"{ai_score}%"
            reason = " ".join(reason_list) if reason_list else "কোড অ্যানালাইসিসে ছবিটিতে কৃত্রিম পরিবর্তনের প্রমাণ পাওয়া গেছে।"
        else:
            status = "Original"
            ai_score = int(max_diff / 2) if max_diff > 0 else 5
            human_score = 100 - ai_score
            confidence = f"{human_score}%"
            reason = "ছবির মেটাডাটা এবং পিক্সেল লেভেল স্বাভাবিক রয়েছে। এটি একটি আসল বা আন-এডিটেড ছবি হওয়ার সম্ভাবনা বেশি।"

        # ফ্রন্টএন্ডের ডোনাট চার্ট ও কার্ডের জন্য সঠিক ফরম্যাটে ডাটা পাঠানো
        return jsonify({
            "status": status,
            "confidence": confidence,
            "reason": reason,
            "ai_score": ai_score,
            "human_score": human_score
        }), 200

    except Exception as e:
        return jsonify({"error": f"ছবিটি প্রসেস করতে কোডে সমস্যা হয়েছে: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
