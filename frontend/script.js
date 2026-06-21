import { initializeApp } from "[https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js](https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js)";
import { getFirestore, doc, setDoc, getDoc, collection, query, getDocs, deleteDoc, addDoc, orderBy } from "[https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js](https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js)";

// 🔥 আপনার দেওয়া আসল ফায়ারবেস কনফিগারেশন
const firebaseConfig = {
  apiKey: "AIzaSyCGSfx5esCvTbK8OYgl-mVuagFOVGo88vo",
  authDomain: "detect-ai-image.firebaseapp.com",
  projectId: "detect-ai-image",
  storageBucket: "detect-ai-image.firebasestorage.app",
  messagingSenderId: "543978852683",
  appId: "1:543978852683:web:0d03e064474ab778dc98ce",
  measurementId: "G-EHXMLPDL2D"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// 🌐 Render-এ আপনার ব্যাকএন্ড লাইভ করার পর প্রাপ্ত URL-টি এখানে বসাবেন
const BACKEND_URL = "[https://your-render-app-name.onrender.com](https://your-render-app-name.onrender.com)"; 

let currentMode = "login"; 
let currentUser = null;
let generatedOTP = null;
let selectedFile = null;
let chartInstance = null;

// DOM উপাদানসমূহ সিলেক্ট করা
const authContainer = document.getElementById('auth-container');
const dashboardContainer = document.getElementById('dashboard-container');
const authTitle = document.getElementById('auth-title');
const nameGroup = document.getElementById('name-group');
const otpGroup = document.getElementById('otp-group');
const passwordGroup = document.getElementById('password-group');
const mainAuthBtn = document.getElementById('main-auth-btn');
const toggleAuthLink = document.getElementById('toggle-auth-link');
const toggleText = document.getElementById('toggle-text');
const forgetPasswordLink = document.getElementById('forget-password-link');
const verifyOtpBtn = document.getElementById('verify-otp-btn');
const passLabel = document.getElementById('pass-label');

// --- অথেন্টিকেশন ইন্টারফেস সুইচ লজিক ---
toggleAuthLink.onclick = (e) => {
    e.preventDefault();
    if(currentMode === "login" || currentMode === "forget") {
        currentMode = "signup";
        authTitle.innerText = "নতুন অ্যাকাউন্ট";
        nameGroup.style.display = "block";
        passwordGroup.style.display = "block";
        passLabel.innerText = "পাসওয়ার্ড সেট করুন";
        mainAuthBtn.innerText = "হোয়াটসঅ্যাপ ওটিপি পাঠান 💬";
        toggleText.innerText = "আগের অ্যাকাউন্ট আছে?";
        toggleAuthLink.innerText = "লগইন করুন";
        otpGroup.style.display = "none";
    } else {
        setLoginMode();
    }
};

forgetPasswordLink.onclick = (e) => {
    e.preventDefault();
    currentMode = "forget";
    authTitle.innerText = "পাসওয়ার্ড রিসেট";
    nameGroup.style.display = "none";
    passwordGroup.style.display = "block";
    passLabel.innerText = "নতুন পাসওয়ার্ড লিখুন";
    mainAuthBtn.innerText = "রিসেট ওটিপি পাঠান 💬";
    toggleText.innerText = "মনে পড়েছে?";
    toggleAuthLink.innerText = "লগইন করুন";
    otpGroup.style.display = "none";
};

function setLoginMode() {
    currentMode = "login";
    authTitle.innerText = "লগইন করুন";
    nameGroup.style.display = "none";
    otpGroup.style.display = "none";
    passwordGroup.style.display = "block";
    passLabel.innerText = "পাসওয়ার্ড";
    mainAuthBtn.innerText = "প্রবেশ করুন 🚀";
    toggleText.innerText = "নতুন অ্যাকাউন্ট তৈরি করবেন?";
    toggleAuthLink.innerText = "সাইন-আপ করুন";
}

// ওটিপি পাঠানো এবং সাধারণ লগইন প্রসেস
mainAuthBtn.onclick = async () => {
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value.trim();
    const name = document.getElementById('user-name').value.trim();

    if(!phone) return alert("দয়া করে একটি মোবাইল নম্বর প্রদান করুন!");

    if(currentMode === "login") {
        if(!password) return alert("পাসওয়ার্ড প্রদান করুন!");
        
        // ফায়ারবেস থেকে ইউজার চেক
        const userDoc = await getDoc(doc(db, "users", phone));
        if(userDoc.exists() && userDoc.data().password === password) {
            loginSuccess(userDoc.data());
        } else {
            alert("❌ ভুল মোবাইল নম্বর অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।");
        }
    } 
    else if(currentMode === "signup" || currentMode === "forget") {
        if(currentMode === "signup" && !name) return alert("আপনার নাম লিখুন!");
        if(!password) return alert("পাসওয়ার্ড টাইপ করুন!");

        // ৬ ডিজিটের ওটিপি কোড জেনারেট
        generatedOTP = Math.floor(100000 + Math.random() * 900000);
        mainAuthBtn.innerText = "Sending OTP...";
        mainAuthBtn.disabled = true;

        // পাইথন ব্যাকএন্ড সার্ভারের মাধ্যমে হোয়াটসঅ্যাপ ওটিপি রিকোয়েস্ট পাঠানো
        try {
            const res = await fetch(`${BACKEND_URL}/api/send-whatsapp-otp`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ phoneNumber: phone, otpCode: generatedOTP })
            });
            const data = await res.json();
            if(res.ok) {
                alert("🎉 সফল হয়েছে! আপনার হোয়াটসঅ্যাপ নম্বরে ওটিপি কোডটি পাঠানো হয়েছে।");
                otpGroup.style.display = "block";
            } else {
                alert("ওটিপি পাঠাতে ব্যর্থ: " + data.message);
                mainAuthBtn.disabled = false;
                mainAuthBtn.innerText = "আবার চেষ্টা করুন 💬";
            }
        } catch (err) {
            alert("ব্যাকএন্ড সার্ভারের সাথে যোগাযোগ করা যাচ্ছে না! লাইভ লিংক ঠিক আছে কি না চেক করুন।");
            mainAuthBtn.disabled = false;
            mainAuthBtn.innerText = "আবার চেষ্টা করুন 💬";
        }
    }
};

// ওটিপি ভেরিফিকেশন কোড চেক করা এবং ফায়ারবেসে ডেটা আপডেট করা
verifyOtpBtn.onclick = async () => {
    const enteredOtp = document.getElementById('otp-code').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value.trim();
    const name = document.getElementById('user-name').value.trim();

    if(enteredOtp === String(generatedOTP)) {
        alert("🎉 অভিনন্দন! ওটিপি ভেরিফিকেশন সফল হয়েছে।");
        
        if(currentMode === "signup") {
            const userData = { phone, name, password };
            await setDoc(doc(db, "users", phone), userData);
            loginSuccess(userData);
        } else if(currentMode === "forget") {
            // পুরাতন অ্যাকাউন্টের পাসওয়ার্ড ফায়ারবেসে ওভাররাইট/আপডেট করা
            const userDoc = await getDoc(doc(db, "users", phone));
            let currentName = "ব্যবহারকারী";
            if(userDoc.exists()) {
                currentName = userDoc.data().name || "ব্যবহারকারী";
            }
            const userData = { phone, name: currentName, password: password };
            await setDoc(doc(db, "users", phone), userData);
            alert("পাসওয়ার্ড সফলভাবে রিসেট হয়েছে। নতুন পাসওয়ার্ড দিয়ে লগইন করুন।");
            setLoginMode();
        }
    } else {
        alert("❌ ভুল ওটিপি কোড! দয়া করে সঠিক কোডটি দিন।");
    }
};

function loginSuccess(user) {
    currentUser = user;
    authContainer.style.display = "none";
    dashboardContainer.style.display = "block";
    document.getElementById('welcome-user').innerText = user.name || user.phone;
    loadHistory();
}

document.getElementById('logout-btn').onclick = () => {
    currentUser = null;
    dashboardContainer.style.display = "none";
    authContainer.style.display = "block";
    setLoginMode();
};

// --- ইমেজ স্ক্যানিং এবং স্ট্রিক্ট ৫-হিস্টোরি রুল ---
const dropZone = document.getElementById('drop-zone');
const imageInput = document.getElementById('image-input');
const previewImg = document.getElementById('preview-img');
const scanBtn = document.getElementById('scan-btn');

dropZone.onclick = () => imageInput.click();
imageInput.onchange = (e) => {
    selectedFile = e.target.files[0];
    if(selectedFile) {
        previewImg.src = URL.createObjectURL(selectedFile);
        previewImg.style.display = "block";
        scanBtn.disabled = false;
    }
};

scanBtn.onclick = async () => {
    if(!selectedFile) return;
    
    document.getElementById('loading').style.display = "block";
    document.getElementById('result-area').style.display = "none";
    scanBtn.disabled = true;

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
        const res = await fetch(`${BACKEND_URL}/api/detect-image`, {
            method: "POST",
            body: formData
        });
        const result = await res.json();
        
        if(res.ok) {
            showResult(result);
            await saveHistoryToFirebase(result);
        } else {
            alert("স্ক্যান করতে সমস্যা হয়েছে: " + (result.error || "Unknown error"));
        }
    } catch (err) {
        alert("সার্ভার থেকে কোনো রেসপন্স পাওয়া যায়নি!");
    } finally {
        document.getElementById('loading').style.display = "none";
        scanBtn.disabled = false;
    }
};

function showResult(data) {
    document.getElementById('result-area').style.display = "block";
    document.getElementById('result-status').innerText = data.status;
    document.getElementById('result-confidence').innerText = data.confidence;
    document.getElementById('result-reason').innerText = data.reason;

    // পুরানো গ্রাফ চার্ট ডেস্ট্রয় করে নতুন চার্ট রেন্ডার করা
    if(chartInstance) chartInstance.destroy();
    const ctx = document.getElementById('resultChart').getContext('2d');
    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['AI Content', 'Original/Human'],
            datasets: [{
                data: [data.ai_score, data.human_score],
                backgroundColor: ['#ef4444', '#34d399'],
                borderWidth: 0
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
}

// 👑 কড়া নিয়ম: নতুন ডাটা সেভ হবে এবং ৫টির বেশি হলেই প্রাচীনতম হিস্টোরি ডিলিট হবে
async function saveHistoryToFirebase(resultData) {
    const historyRef = collection(db, "users", currentUser.phone, "history");
    
    // ১. নতুন স্ক্যান ডাটা যোগ করা
    await addDoc(historyRef, {
        status: resultData.status,
        confidence: resultData.confidence,
        timestamp: Date.now()
    });

    // ২. বর্তমান ইউজারের সমস্ত হিস্টোরি রিকোয়েস্ট করা (টাইমস্ট্যাম্পের ক্রমানুসারে)
    const q = query(historyRef, orderBy("timestamp", "desc"));
    const querySnapshot = await getDocs(q);
    
    // ৩. সাইজ ৫ এর বেশি হলে অতিরিক্ত ফাইলগুলো লুপ চালিয়ে ডিলিট করা
    if (querySnapshot.size > 5) {
        for (let i = 5; i < querySnapshot.size; i++) {
            const docToDelete = querySnapshot.docs[i].ref;
            await deleteDoc(docToDelete); // ফায়ারবেস ফায়ারস্টোর থেকে সরাসরি রিমুভ
        }
    }
    
    loadHistory();
}

// ড্যাশবোর্ডে হিস্টোরি রেন্ডার বা শো করার ফাংশন
async function loadHistory() {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = "";
    
    const historyRef = collection(db, "users", currentUser.phone, "history");
    const q = query(historyRef, orderBy("timestamp", "desc"));
    const querySnapshot = await getDocs(q);

    if(querySnapshot.empty) {
        historyList.innerHTML = '<p class="empty-text">কোনো হিস্টোরি পাওয়া যায়নি।</p>';
        return;
    }

    querySnapshot.forEach((doc) => {
        const item = doc.data();
        const date = new Date(item.timestamp).toLocaleString('bn-BD');
        historyList.innerHTML += `
            <div class="history-item">
                <h4>${item.status} (${item.confidence})</h4>
                <p>তারিখ: ${date}</p>
            </div>
        `;
    });
}
