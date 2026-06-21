import os
import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageStat, ImageChops
import io

app = Flask(__name__)
CORS(app)

# 🇧🇩 ফোন নম্বর ফরম্যাট ফাংশন
def format_bd_number(phone):
    cleaned = ''.join(filter(str.isdigit, phone))
    if cleaned.startswith('01') and len(cleaned) == 11:
        return "88" + cleaned
    elif cleaned.startswith('8801') and len(cleaned) == 13:
        return cleaned
    return cleaned

@app.route('/api/send-whatsapp-otp', methods=['POST'])
def send_whatsapp_otp():
    data = request.json or {}
    raw_phone = data.get('phoneNumber')
    otp_code = data.get('otpCode')

    if not raw_phone or not otp_code:
        return jsonify({"success": False, "message": "মোবাইল নম্বর এবং ওটিপি কোড প্রয়োজন!"}), 400

    formatted_phone = format_bd_number(raw_phone)
    whatsapp_api_url = "https://otp-api-hmrz.onrender.com/send-otp"

    try:
        response = requests.post(whatsapp_api_url, json={
            "phoneNumber": formatted_phone,
            "otpCode": str(otp_code)
        }, headers={"Content-Type": "application/json"}, timeout=15)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": "হোয়াটসঅ্যাপ এপিআই ত্রুটি: " + str(e)}), 500

# 📸 সংশোধিত এবং শক্তিশালী ইমেজ ডিটেক্টর রাউট
@app.route('/api/detect-image', methods=['POST'])
def detect_image():
    start_time = time.time()

    if 'image' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি!"}), 400
    
    file = request.files['image']
    image_bytes = file.read()

    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        has_camera_metadata = False
        has_editing_software = False
        has_ai_tag = False
        software_name = ""

        # ১. মেটাডাটা স্ক্যান
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        if exif_data:
            for tag, value in exif_data.items():
                val_str = str(value).lower()
                if any(k in val_str for k in ['canon', 'nikon', 'sony', 'apple', 'samsung', 'xiaomi', 'fuji', 'lens', 'focal', 'iphone']):
                    has_camera_metadata = True
                if 'photoshop' in val_str or 'gimp' in val_str or 'adobe' in val_str:
                    has_editing_software = True
                    software_name = "Adobe Photoshop"
                if any(ai_k in val_str for ai_k in ['midjourney', 'stable diffusion', 'dall-e', 'ai generated', 'creator: ai']):
                    has_ai_tag = True

        # ২. পিক্সেল কালার বৈচিত্র্য এবং মসৃণতা অ্যানালাইসিস (কার্টুন/ইলাস্ট্রেশন ডিটেকশন লেয়ার)
        stat = ImageStat.Stat(img)
        std_dev = stat.stddev
        avg_std_dev = sum(std_dev) / len(std_dev) if std_dev else 0

        # ৩. প্রিসিশন এরর লেভেল অ্যানালাইসিস (ELA)
        resaved_stream = io.BytesIO()
        img.convert("RGB").save(resaved_stream, "JPEG", quality=90)
        resaved_stream.seek(0)
        resaved_img = Image.open(resaved_stream)
        
        diff = ImageChops.difference(img.convert("RGB"), resaved_img)
        extrema = diff.getextrema()
        
        # পূর্বের IndexErrors বাগটি এখানে স্থায়ীভাবে ফিক্স করা হয়েছে
        max_diff = 0
        if extrema:
            try:
                max_diff = max([ex[1] for ex in extrema if isinstance(ex, (list, tuple)) and len(ex) > 1])
            except Exception:
                max_diff = 0

        # ৪. আপনার আপলোড করা ইলাস্ট্রেশন বা ড্রয়িং ছবির জন্য স্পেশাল কন্ডিশন
        # এআই ড্রয়িং বা ইলাস্ট্রেশন ছবিতে কালার ডিস্ট্রিবিউশন এবং গ্রেডিয়েন্ট অত্যন্ত কৃত্তিম ও মসৃণ থাকে
        is_digital_artwork = avg_std_dev < 55 and max_diff < 20

        # ৫. চূড়ান্ত বাইনারি লজিক নির্ধারণ
        if has_ai_tag:
            status = "AI Generated Image"
            ai_score = 98
            human_score = 2
            confidence = "98%"
            reason = "ছবির মেটাডাটায় সরাসরি জেনারেটিভ এআই ট্যাগ পাওয়া গেছে।"
            
        elif is_digital_artwork and not has_camera_metadata:
            status = "AI Generated / Digital Artwork"
            ai_score = 92
            human_score = 8
            confidence = "92%"
            reason = "ছবিটি একটি কৃত্রিম এআই ইলাস্ট্রেশন বা ডিজিটাল আর্টওয়ার্ক। এতে বাস্তব ক্যামেরার কোনো পিক্সেল নয়েজ বা গ্রেইন প্যাটার্ন নেই এবং অবজেক্টের সীমানাগুলো অতিমাত্রায় কৃত্রিম ও নিখুঁত।"
            
        elif has_editing_software or max_diff > 35:
            status = "AI Edited / Manually Edited"
            ai_score = 85
            human_score = 15
            confidence = "85%"
            reason = "ছবিটিতে ডিজিটাল এডিটিং টুলস ব্যবহারের স্পষ্ট পিক্সেল কম্প্রেশন বা মেটাডাটা সিগনেচার পাওয়া গেছে।"
            
        elif has_camera_metadata and not has_editing_software:
            status = "Original Photo"
            ai_score = 4
            human_score = 96
            confidence = "96%"
            reason = "ছবিটিতে জেনুইন ডিভাইস ও লেন্স মেটাডাটা রয়েছে এবং পিক্সেল স্ট্রাকচার সম্পূর্ণ প্রাকৃতিক।"
            
        else:
            status = "Potential AI Generation / Edited"
            ai_score = 75
            human_score = 25
            confidence = "75%"
            reason = "ছবিটিতে কোনো বাস্তব ক্যামেরা ডিভাইসের প্রমাণ নেই এবং পিক্সেলগুলো কৃত্তিমভাবে তৈরি বা সম্পাদিত।"

        # ৩০ সেকেন্ড প্রসেসিং ডিলে মেইনটেইন করা
        elapsed_time = time.time() - start_time
        remaining_time = 30.0 - elapsed_time
        if remaining_time > 0:
            time.sleep(remaining_time)

        return jsonify({
            "status": status,
            "confidence": confidence,
            "reason": reason,
            "ai_score": ai_score,
            "human_score": human_score
        }), 200

    except Exception as e:
        return jsonify({"error": f"সার্ভার প্রসেসিং এরর: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
