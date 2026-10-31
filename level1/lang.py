# -*- coding: utf-8 -*-
"""Grahak Seva - multilingual layer (English + Hindi, Bengali, Tamil, Telugu, Marathi).

Two jobs:
  1. UI text      tr("Chat")                       -> the label in the selected language
  2. Conversation to_english(text, lang)           -> customer's message, translated for the five agents
                  localize_response(res, lang)     -> the agents' final reply, in the customer's language

The five agents themselves stay English-only. Customer text is translated in, the agents run, and the
reply is translated out. Both translation steps are written into the agent trace.

How text gets translated (best first):
  a) hand-written tables below (UI labels and the A5 follow-up / escalation messages) - work offline
  b) translations_cache.json (filled by warm_translations.py, or by earlier live runs) - work offline
  c) live machine translation through `deep-translator` (needs internet: pip install deep-translator)
  d) English, when none of the above is available. Nothing ever crashes because a translation is missing.

To add a language: add it to LANGS, add one column to every row of UI / A5 below, add its code to GOOGLE_CODE.
The hand-written Indian-language text should be reviewed by a native speaker before a public demo.
"""
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE_FILE = HERE / "translations_cache.json"

# code -> (native name, English name)
LANGS = {
    "en": ("English", "English"),
    "hi": ("हिन्दी", "Hindi"),
    "bn": ("বাংলা", "Bengali"),
    "ta": ("தமிழ்", "Tamil"),
    "te": ("తెలుగు", "Telugu"),
    "mr": ("मराठी", "Marathi"),
}
ORDER = list(LANGS)                    # column order used in the tables below: en, hi, bn, ta, te, mr
GOOGLE_CODE = {c: c for c in LANGS}    # codes used by the live translator

# --------------------------------------------------------------------------- UI text
# English text -> (hi, bn, ta, te, mr).  {store}, {n} etc. are filled in by tr(..., store=...).
UI = {
    # sidebar
    "Stores": ("स्टोर", "স্টোর", "கடைகள்", "స్టోర్లు", "स्टोअर्स"),
    "Language": ("भाषा", "ভাষা", "மொழி", "భాష", "भाषा"),
    "Pick a store to see its support dashboard and chat with its assistant.": (
        "किसी स्टोर का सपोर्ट डैशबोर्ड देखने और उसके असिस्टेंट से चैट करने के लिए स्टोर चुनें।",
        "স্টোরের সাপোর্ট ড্যাশবোর্ড দেখতে এবং তার সহকারীর সঙ্গে চ্যাট করতে একটি স্টোর বেছে নিন।",
        "ஒரு கடையின் ஆதரவு டாஷ்போர்டைப் பார்க்கவும் அதன் உதவியாளருடன் அரட்டையடிக்கவும் கடையைத் தேர்ந்தெடுக்கவும்.",
        "ఒక స్టోర్ సపోర్ట్ డ్యాష్‌బోర్డ్ చూడటానికి మరియు దాని అసిస్టెంట్‌తో చాట్ చేయడానికి స్టోర్‌ను ఎంచుకోండి.",
        "स्टोअरचा सपोर्ट डॅशबोर्ड पाहण्यासाठी आणि त्याच्या असिस्टंटशी चॅट करण्यासाठी स्टोअर निवडा."),
    "Demo: all stores use the same five agents on their own slice of the Bitext data. No real store data or APIs.": (
        "डेमो: सभी स्टोर एक ही पाँच एजेंट और Bitext डेटा का अपना-अपना हिस्सा इस्तेमाल करते हैं। कोई असली स्टोर डेटा या API नहीं है।",
        "ডেমো: সব স্টোর একই পাঁচটি এজেন্ট এবং Bitext ডেটার নিজস্ব অংশ ব্যবহার করে। কোনো আসল স্টোর ডেটা বা API নেই।",
        "டெமோ: எல்லா கடைகளும் ஒரே ஐந்து முகவர்களையும் Bitext தரவின் தங்கள் பகுதியையும் பயன்படுத்துகின்றன. உண்மையான கடை தரவு அல்லது API இல்லை.",
        "డెమో: అన్ని స్టోర్లు ఒకే ఐదు ఏజెంట్లను, Bitext డేటాలోని తమ భాగాన్ని ఉపయోగిస్తాయి. నిజమైన స్టోర్ డేటా లేదా API లేదు.",
        "डेमो: सर्व स्टोअर्स तेच पाच एजंट आणि Bitext डेटाचा स्वतःचा भाग वापरतात. खरा स्टोअर डेटा किंवा API नाही."),
    # navigation
    "Dashboard": ("डैशबोर्ड", "ড্যাশবোর্ড", "டாஷ்போர்டு", "డ్యాష్‌బోర్డ్", "डॅशबोर्ड"),
    "New query": ("नया प्रश्न", "নতুন প্রশ্ন", "புதிய கேள்வி", "కొత్త ప్రశ్న", "नवीन प्रश्न"),
    "Workspace": ("वर्कस्पेस", "ওয়ার্কস্পেস", "பணியிடம்", "వర్క్‌స్పేస్", "वर्कस्पेस"),
    "Insights": ("इनसाइट्स", "ইনসাইটস", "நுண்ணறிவுகள்", "ఇన్‌సైట్స్", "इनसाइट्स"),
    "Copy email": ("ईमेल कॉपी करें", "ইমেল কপি করুন", "மின்னஞ்சலை நகலெடு", "ఇమెయిల్ కాపీ చేయండి", "ईमेल कॉपी करा"),
    "Chat": ("चैट", "চ্যাট", "அரட்டை", "చాట్", "चॅट"),
    "Agent workings": ("एजेंट कैसे काम करते हैं", "এজেন্টদের কাজ", "முகவர்களின் செயல்பாடு", "ఏజెంట్ల పని", "एजंट कसे काम करतात"),
    "History": ("इतिहास", "ইতিহাস", "வரலாறு", "చరిత్ర", "इतिहास"),
    "Ask a question, get an answer": ("सवाल पूछें, जवाब पाएँ", "প্রশ্ন করুন, উত্তর পান", "கேள்வி கேளுங்கள், பதில் பெறுங்கள", "ప్రశ్న అడగండి, సమాధానం పొందండి", "प्रश्न विचारा, उत्तर मिळवा"),
    "See how the five agents handled it": ("देखें कि पाँच एजेंटों ने इसे कैसे संभाला", "দেখুন পাঁচটি এজেন্ট কীভাবে সামলেছে", "ஐந்து முகவர்கள் இதை எப்படிக் கையாண்டனர் என்று பாருங்கள்", "ఐదు ఏజెంట్లు దీన్ని ఎలా నిర్వహించాయో చూడండి", "पाच एजंटनी हे कसे हाताळले ते पहा"),
    "Search every past query": ("पिछले सभी प्रश्न खोजें", "আগের সব প্রশ্ন খুঁজুন", "முந்தைய அனைத்து கேள்விகளையும் தேடுங்கள்", "గత ప్రశ్నలన్నీ వెతకండి", "मागील सर्व प्रश्न शोधा"),
    "Overview": ("अवलोकन", "ওভারভিউ", "மேலோட்டம்", "అవలోకనం", "आढावा"),
    "Live metrics and charts": ("लाइव मेट्रिक्स और चार्ट", "লাইভ মেট্রিক্স ও চার্ট", "நேரடி அளவீடுகளும் வரைபடங்களும்", "లైవ్ మెట్రిక్స్ మరియు చార్ట్‌లు", "लाइव्ह मेट्रिक्स आणि चार्ट"),
    "Reports": ("रिपोर्ट", "রিপোর্ট", "அறிக்கைகள்", "నివేదికలు", "अहवाल"),
    "Jump to a section": ("किसी भाग पर जाएँ", "একটি বিভাগে যান", "ஒரு பகுதிக்குச் செல்லுங்கள்", "ఒక విభాగానికి వెళ్ళండి", "एका विभागात जा"),
    "Confidence over time": ("समय के साथ विश्वास स्तर", "সময়ের সাথে আত্মবিশ্বাস", "காலப்போக்கில் நம்பிக்கை", "కాలక్రమేణా విశ్వాసం", "वेळेनुसार आत्मविश्वास"),
    "Threshold table": ("सीमा तालिका", "থ্রেশহোল্ড টেবিল", "வரம்பு அட்டவணை", "థ్రెషోల్డ్ పట్టిక", "मर्यादा तक्ता"),
    "Weakest intents": ("सबसे कमज़ोर इरादे", "সবচেয়ে দুর্বল উদ্দেশ্য", "பலவீனமான நோக்கங்கள்", "బలహీనమైన ఉద్దేశ్యాలు", "सर्वात कमकुवत उद्देश"),
    # header of the chat page
    "{store} support": ("{store} सहायता", "{store} সাপোর্ট", "{store} ஆதரவு", "{store} సపోర్ట్", "{store} सहाय्य"),
    "Ask a question and get an answer. Open any reply to see how the five agents worked it out.": (
        "कोई सवाल पूछें और जवाब पाएँ। किसी भी उत्तर को खोलकर देखें कि पाँच एजेंटों ने उसे कैसे तैयार किया।",
        "একটি প্রশ্ন করুন এবং উত্তর পান। যেকোনো উত্তর খুলে দেখুন পাঁচটি এজেন্ট কীভাবে সেটি তৈরি করেছে।",
        "ஒரு கேள்வியைக் கேட்டு பதிலைப் பெறுங்கள். எந்தப் பதிலையும் திறந்து ஐந்து முகவர்கள் அதை எப்படி உருவாக்கினர் என்று பாருங்கள்.",
        "ఒక ప్రశ్న అడిగి సమాధానం పొందండి. ఏ సమాధానాన్నైనా తెరిచి ఐదు ఏజెంట్లు దాన్ని ఎలా రూపొందించాయో చూడండి.",
        "एखादा प्रश्न विचारा आणि उत्तर मिळवा. कोणतेही उत्तर उघडून पाच एजंटनी ते कसे तयार केले ते पहा."),
    "+ New chat": ("+ नई चैट", "+ নতুন চ্যাট", "+ புதிய அரட்டை", "+ కొత్త చాట్", "+ नवीन चॅट"),
    "Export traces": ("ट्रेस एक्सपोर्ट करें", "ট্রেস এক্সপোর্ট করুন", "தடங்களை ஏற்றுமதி செய்", "ట్రేస్‌లను ఎగుమతి చేయండి", "ट्रेस एक्सपोर्ट करा"),
    "Escalation threshold": ("एस्केलेशन सीमा", "এসকালেশন সীমা", "உயர்த்தல் வரம்பு", "ఎస్కలేషన్ పరిమితి", "एस्केलेशन मर्यादा"),
    "Confidence below this goes to a human": (
        "इससे कम विश्वास स्तर वाले प्रश्न इंसान के पास जाते हैं", "এর চেয়ে কম আত্মবিশ্বাস হলে মানুষের কাছে যায়",
        "இதற்குக் குறைவான நம்பிக்கை உள்ளவை மனிதரிடம் செல்லும்", "దీని కంటే తక్కువ విశ్వాసం ఉంటే మనిషికి వెళ్తుంది",
        "यापेक्षा कमी आत्मविश्वास असल्यास प्रश्न माणसाकडे जातो"),
    "{store} help centre ↗": ("{store} हेल्प सेंटर ↗", "{store} হেল্প সেন্টার ↗", "{store} உதவி மையம் ↗", "{store} హెల్ప్ సెంటర్ ↗", "{store} हेल्प सेंटर ↗"),
    # chat
    "Hi, I'm the {store} support assistant (powered by Grahak Seva). Ask me about orders, refunds, shipping, payments or your account.": (
        "नमस्ते! मैं {store} का सपोर्ट असिस्टेंट हूँ (ग्राहक सेवा द्वारा संचालित)। ऑर्डर, रिफंड, शिपिंग, भुगतान या अपने खाते के बारे में पूछें।",
        "নমস্কার! আমি {store}-এর সাপোর্ট সহকারী (গ্রাহক সেবা চালিত)। অর্ডার, রিফান্ড, শিপিং, পেমেন্ট বা আপনার অ্যাকাউন্ট সম্পর্কে জিজ্ঞাসা করুন।",
        "வணக்கம்! நான் {store} ஆதரவு உதவியாளர் (கிராஹக் சேவா மூலம் இயங்குகிறது). ஆர்டர்கள், பணத்தைத் திரும்பப் பெறுதல், அனுப்புதல், கட்டணம் அல்லது உங்கள் கணக்கு பற்றி கேளுங்கள்.",
        "నమస్కారం! నేను {store} సపోర్ట్ అసిస్టెంట్‌ని (గ్రాహక్ సేవా ఆధారితం). ఆర్డర్లు, రీఫండ్లు, షిప్పింగ్, చెల్లింపులు లేదా మీ ఖాతా గురించి అడగండి.",
        "नमस्कार! मी {store} चा सपोर्ट असिस्टंट आहे (ग्राहक सेवा द्वारे चालवलेला). ऑर्डर, परतावा, शिपिंग, पेमेंट किंवा तुमच्या खात्याबद्दल विचारा."),
    "Ask a question, e.g. How can I request a refund?": (
        "प्रश्न पूछें, जैसे: मैं रिफंड के लिए अनुरोध कैसे करूँ?", "প্রশ্ন করুন, যেমন: আমি কীভাবে রিফান্ডের অনুরোধ করব?",
        "கேள்வி கேளுங்கள், எ.கா: பணத்தைத் திரும்பப் பெற எப்படி கோருவது?", "ప్రశ్న అడగండి, ఉదా: రీఫండ్ కోసం ఎలా అభ్యర్థించాలి?",
        "प्रश्न विचारा, उदा: परताव्यासाठी विनंती कशी करू?"),
    "How the agents handled this": ("एजेंटों ने इसे कैसे संभाला", "এজেন্টরা এটি কীভাবে সামলেছে", "முகவர்கள் இதை எப்படிக் கையாண்டனர்", "ఏజెంట్లు దీన్ని ఎలా నిర్వహించాయి", "एजंटनी हे कसे हाताळले"),
    "Recommended for human review": ("मानव समीक्षा के लिए अनुशंसित", "মানুষের পর্যালোচনার জন্য সুপারিশ করা হয়েছে", "மனித மதிப்பாய்வுக்குப் பரிந்துரைக்கப்பட்டது", "మానవ సమీక్షకు సిఫార్సు చేయబడింది", "मानवी पुनरावलोकनासाठी शिफारस"),
    "Needs a few details": ("कुछ जानकारी चाहिए", "কিছু তথ্য দরকার", "சில விவரங்கள் தேவை", "కొన్ని వివరాలు కావాలి", "काही माहिती हवी आहे"),
    "Thanks, that helps. Here is what to do:": (
        "धन्यवाद, इससे मदद मिली। आपको यह करना है:", "ধন্যবাদ, এটি সাহায্য করেছে। আপনাকে যা করতে হবে:",
        "நன்றி, இது உதவியது. நீங்கள் செய்ய வேண்டியது:", "ధన్యవాదాలు, ఇది సహాయపడింది. మీరు చేయవలసినది:", "धन्यवाद, यामुळे मदत झाली. तुम्हाला हे करायचे आहे:"),
    "I can't find it": ("मुझे नहीं मिल रहा", "আমি খুঁজে পাচ্ছি না", "என்னால் கண்டுபிடிக்க முடியவில்லை", "నాకు దొరకడం లేదు", "मला सापडत नाही"),
    "I don't have any of these": ("मेरे पास इनमें से कुछ भी नहीं है", "আমার কাছে এর কোনোটিই নেই", "இவற்றில் எதுவும் என்னிடம் இல்லை", "నా దగ్గర వీటిలో ఏదీ లేదు", "माझ्याकडे यापैकी काहीही नाही"),
    # connecting / contact card
    "Connecting to {store} support...": ("{store} सपोर्ट से जुड़ रहे हैं...", "{store} সাপোর্টের সঙ্গে সংযোগ হচ্ছে...", "{store} ஆதரவுடன் இணைகிறது...", "{store} సపోర్ట్‌కు కనెక్ట్ అవుతోంది...", "{store} सपोर्टशी जोडत आहे..."),
    "Connected to {store} support": ("{store} सपोर्ट से जुड़ गए", "{store} সাপোর্টের সঙ্গে সংযুক্ত হয়েছে", "{store} ஆதரவுடன் இணைக்கப்பட்டது", "{store} సపోర్ట్‌కు కనెక్ట్ అయింది", "{store} सपोर्टशी जोडले गेले"),
    "Talk to a person at {store}": ("{store} के किसी व्यक्ति से बात करें", "{store}-এর একজন ব্যক্তির সঙ্গে কথা বলুন", "{store} நிறுவனத்தின் ஒருவருடன் பேசுங்கள்", "{store}లో ఒక వ్యక్తితో మాట్లాడండి", "{store} मधील एका व्यक्तीशी बोला"),
    "Phone": ("फ़ोन", "ফোন", "தொலைபேசி", "ఫోన్", "फोन"),
    "Email": ("ईमेल", "ইমেল", "மின்னஞ்சல்", "ఇమెయిల్", "ईमेल"),
    "Hours": ("समय", "সময়", "நேரம்", "సమయాలు", "वेळ"),
    "In the app": ("ऐप में", "অ্যাপে", "செயலியில்", "యాప్‌లో", "अॅपमध्ये"),
    "Help centre": ("हेल्प सेंटर", "হেল্প সেন্টার", "உதவி மையம்", "హెల్ప్ సెంటర్", "हेल्प सेंटर"),
    "{store} customer support": ("{store} कस्टमर सपोर्ट", "{store} কাস্টমার সাপোর্ট", "{store} வாடிக்கையாளர் ஆதரவு", "{store} కస్టమర్ సపోర్ట్", "{store} कस्टमर सपोर्ट"),
    "Demo build: confirm these contact options on {store}'s official website.": (
        "डेमो बिल्ड: ये संपर्क विकल्प {store} की आधिकारिक वेबसाइट पर जाँच लें।", "ডেমো বিল্ড: এই যোগাযোগের বিকল্পগুলি {store}-এর অফিসিয়াল ওয়েবসাইটে যাচাই করুন।",
        "டெமோ பதிப்பு: இந்தத் தொடர்பு விருப்பங்களை {store} இன் அதிகாரப்பூர்வ இணையதளத்தில் உறுதிசெய்யுங்கள்.",
        "డెమో బిల్డ్: ఈ సంప్రదింపు ఎంపికలను {store} అధికారిక వెబ్‌సైట్‌లో నిర్ధారించుకోండి.",
        "डेमो बिल्ड: हे संपर्क पर्याय {store} च्या अधिकृत वेबसाइटवर तपासा."),
    # dashboard (home.html)
    "{store} support dashboard": ("{store} सपोर्ट डैशबोर्ड", "{store} সাপোর্ট ড্যাশবোর্ড", "{store} ஆதரவு டாஷ்போர்டு", "{store} సపోర్ట్ డ్యాష్‌బోర్డ్", "{store} सपोर्ट डॅशबोर्ड"),
    "Chat with {store}": ("{store} से चैट करें", "{store}-এর সঙ্গে চ্যাট করুন", "{store} உடன் அரட்டை", "{store}తో చాట్ చేయండి", "{store} शी चॅट करा"),
    "Queries handled": ("संभाले गए प्रश्न", "সামলানো প্রশ্ন", "கையாளப்பட்ட கேள்விகள்", "నిర్వహించిన ప్రశ్నలు", "हाताळलेले प्रश्न"),
    "Answered by agents": ("एजेंटों द्वारा उत्तर दिए गए", "এজেন্টদের উত্তর দেওয়া", "முகவர்கள் பதிலளித்தவை", "ఏజెంట్లు సమాధానం ఇచ్చినవి", "एजंटनी उत्तर दिलेले"),
    "Escalated to humans": ("मनुष्यों को भेजे गए", "মানুষের কাছে পাঠানো", "மனிதர்களிடம் அனுப்பப்பட்டவை", "మనుషులకు పంపినవి", "माणसांकडे पाठवलेले"),
    "Avg. response time": ("औसत प्रतिक्रिया समय", "গড় প্রতিক্রিয়া সময়", "சராசரி பதில் நேரம்", "సగటు ప్రతిస్పందన సమయం", "सरासरी प्रतिसाद वेळ"),
    "held-out sample": ("परीक्षण नमूना", "পরীক্ষামূলক নমুনা", "சோதனை மாதிரி", "పరీక్ష నమూనా", "चाचणी नमुना"),
    "A1 to A5 end to end": ("A1 से A5 तक पूरा", "A1 থেকে A5 পর্যন্ত সম্পূর্ণ", "A1 முதல் A5 வரை முழுமையாக", "A1 నుండి A5 వరకు పూర్తిగా", "A1 ते A5 पूर्ण"),
    "Query volume": ("प्रश्नों की संख्या", "প্রশ্নের পরিমাণ", "கேள்வி அளவு", "ప్రశ్నల పరిమాణం", "प्रश्नांची संख्या"),
    "Validation replay": ("वैलिडेशन रीप्ले", "ভ্যালিডেশন রিপ্লে", "சரிபார்ப்பு மறுஒளிபரப்பு", "వ్యాలిడేషన్ రీప్లే", "व्हॅलिडेशन रीप्ले"),
    "Top intents": ("शीर्ष इरादे", "শীর্ষ উদ্দেশ্য", "முக்கிய நோக்கங்கள்", "ప్రధాన ఉద్దేశ్యాలు", "प्रमुख उद्देश"),
    "Recent queries": ("हाल के प्रश्न", "সাম্প্রতিক প্রশ্ন", "சமீபத்திய கேள்விகள்", "ఇటీవలి ప్రశ్నలు", "अलीकडील प्रश्न"),
    "View all": ("सभी देखें", "সব দেখুন", "அனைத்தையும் பார்", "అన్నీ చూడండి", "सर्व पहा"),
    "Customer query": ("ग्राहक का प्रश्न", "গ্রাহকের প্রশ্ন", "வாடிக்கையாளர் கேள்வி", "కస్టమర్ ప్రశ్న", "ग्राहकाचा प्रश्न"),
    "Intent": ("इरादा", "উদ্দেশ্য", "நோக்கம்", "ఉద్దేశ్యం", "उद्देश"),
    "Confidence": ("विश्वास स्तर", "আত্মবিশ্বাস", "நம்பிக்கை", "విశ్వాసం", "आत्मविश्वास"),
    "Action": ("कार्रवाई", "ক্রিয়া", "நடவடிக்கை", "చర్య", "कृती"),
    "When": ("कब", "কখন", "எப்போது", "ఎప్పుడు", "केव्हा"),
    "Answered": ("उत्तर दिया", "উত্তর দেওয়া হয়েছে", "பதிலளிக்கப்பட்டது", "సమాధానం ఇచ్చారు", "उत्तर दिले"),
    "Clarify": ("स्पष्टीकरण", "ব্যাখ্যা চাওয়া", "தெளிவுபடுத்து", "స్పష్టత", "स्पष्टीकरण"),
    "Escalated": ("एस्केलेट किया", "এসকালেট করা হয়েছে", "உயர்த்தப்பட்டது", "ఎస్కలేట్ చేశారు", "एस्केलेट केले"),
    "Resolved by agents": ("एजेंटों द्वारा हल", "এজেন্টদের দ্বারা সমাধান", "முகவர்களால் தீர்க்கப்பட்டது", "ఏజెంట్లు పరిష్కరించినవి", "एजंटनी सोडवलेले"),
    "Search": ("खोजें", "খুঁজুন", "தேடு", "వెతకండి", "शोधा"),
    "Export": ("एक्सपोर्ट", "এক্সপোর্ট", "ஏற்றுமதி", "ఎగుమతి", "एक्सपोर्ट"),
    "weekly": ("साप्ताहिक", "সাপ্তাহিক", "வாராந்திர", "వారపు", "साप्ताहिक"),
    "monthly": ("मासिक", "মাসিক", "மாதாந்திர", "నెలవారీ", "मासिक"),
    "yearly": ("वार्षिक", "বার্ষিক", "ஆண்டுதோறும்", "వార్షిక", "वार्षिक"),
    "All": ("सभी", "সব", "அனைத்தும்", "అన్నీ", "सर्व"),
    "{store} support · {n} held-out customer queries handled by the five agents.": (
        "{store} सहायता · पाँच एजेंटों ने {n} परीक्षण ग्राहक प्रश्न संभाले।", "{store} সাপোর্ট · পাঁচটি এজেন্ট {n}টি পরীক্ষামূলক গ্রাহক প্রশ্ন সামলেছে।",
        "{store} ஆதரவு · ஐந்து முகவர்கள் {n} சோதனை வாடிக்கையாளர் கேள்விகளைக் கையாண்டனர்.", "{store} సపోర్ట్ · ఐదు ఏజెంట్లు {n} పరీక్ష కస్టమర్ ప్రశ్నలను నిర్వహించాయి.",
        "{store} सहाय्य · पाच एजंटनी {n} चाचणी ग्राहक प्रश्न हाताळले."),
    "Simulated {store} slice of the Bitext validation split (threshold {th}). Not real {store} data.": (
        "Bitext वैलिडेशन डेटा का सिमुलेटेड {store} हिस्सा (सीमा {th})। यह असली {store} डेटा नहीं है।", "Bitext ভ্যালিডেশন ডেটার সিমুলেটেড {store} অংশ (সীমা {th})। এটি আসল {store} ডেটা নয়।",
        "Bitext சரிபார்ப்புத் தரவின் உருவகப்படுத்தப்பட்ட {store} பகுதி (வரம்பு {th}). இது உண்மையான {store} தரவு அல்ல.", "Bitext వ్యాలిడేషన్ డేటాలోని అనుకరించిన {store} భాగం (పరిమితి {th}). ఇది నిజమైన {store} డేటా కాదు.",
        "Bitext व्हॅलिडेशन डेटाचा सिम्युलेटेड {store} भाग (मर्यादा {th}). हा खरा {store} डेटा नाही."),
    "{p}% needed a follow-up": ("{p}% को फ़ॉलो-अप चाहिए था", "{p}%-এর ফলো-আপ দরকার ছিল", "{p}% க்கு தொடர் கேள்வி தேவைப்பட்டது", "{p}%కు ఫాలో-అప్ అవసరమైంది", "{p}% ना पाठपुरावा हवा होता"),
    "{p}% of queries": ("{p}% प्रश्न", "{p}% প্রশ্ন", "{p}% கேள்விகள்", "{p}% ప్రశ్నలు", "{p}% प्रश्न"),
}

# --------------------------------------------------------------------------- A5 reply templates
# The agents' follow-up questions and escalation message are fixed English templates, so they are
# translated here by hand (offline, consistent) instead of by machine translation.
A5 = {
    "missing": (
        "No problem, that happens a lot. Your order number is usually in the confirmation email or under *My Orders* in your account. If you can't find it, tell me the **email or phone number** you used at checkout, or the **item name and roughly when you bought it**, and I'll work from that.",
        "कोई बात नहीं, ऐसा अक्सर होता है। आपका ऑर्डर नंबर आमतौर पर कन्फ़र्मेशन ईमेल में या आपके खाते में *मेरे ऑर्डर* के अंतर्गत होता है। अगर वह नहीं मिल रहा, तो चेकआउट पर इस्तेमाल किया गया **ईमेल या फ़ोन नंबर**, या **सामान का नाम और लगभग कब खरीदा** बताइए, मैं उसी से आगे बढ़ूँगा।",
        "কোনো সমস্যা নেই, এটা প্রায়ই হয়। আপনার অর্ডার নম্বর সাধারণত কনফার্মেশন ইমেলে বা অ্যাকাউন্টের *আমার অর্ডার* অংশে থাকে। না পেলে চেকআউটে ব্যবহার করা **ইমেল বা ফোন নম্বর**, অথবা **পণ্যের নাম এবং মোটামুটি কখন কিনেছেন** জানান, আমি সেটা দিয়েই এগোব।",
        "பரவாயில்லை, இது அடிக்கடி நடப்பதுதான். உங்கள் ஆர்டர் எண் பொதுவாக உறுதிப்படுத்தல் மின்னஞ்சலில் அல்லது உங்கள் கணக்கில் *எனது ஆர்டர்கள்* பகுதியில் இருக்கும். கிடைக்கவில்லை என்றால், பணம் செலுத்தும்போது பயன்படுத்திய **மின்னஞ்சல் அல்லது தொலைபேசி எண்ணை**, அல்லது **பொருளின் பெயரையும் எப்போது வாங்கினீர்கள் என்பதையும்** சொல்லுங்கள், அதை வைத்து தொடர்கிறேன்.",
        "పర్వాలేదు, ఇలా తరచుగా జరుగుతుంది. మీ ఆర్డర్ నంబర్ సాధారణంగా కన్ఫర్మేషన్ ఇమెయిల్‌లో లేదా మీ ఖాతాలో *నా ఆర్డర్లు* కింద ఉంటుంది. అది దొరక్కపోతే, చెక్అవుట్‌లో ఉపయోగించిన **ఇమెయిల్ లేదా ఫోన్ నంబర్**, లేదా **వస్తువు పేరు మరియు సుమారుగా ఎప్పుడు కొన్నారో** చెప్పండి, దాని ఆధారంగా కొనసాగిస్తాను.",
        "काही हरकत नाही, असे वारंवार घडते. तुमचा ऑर्डर नंबर साधारणपणे कन्फर्मेशन ईमेलमध्ये किंवा तुमच्या खात्यातील *माझे ऑर्डर* मध्ये असतो. तो सापडत नसेल, तर चेकआउटवेळी वापरलेला **ईमेल किंवा फोन नंबर**, किंवा **वस्तूचे नाव आणि साधारण केव्हा खरेदी केली** ते सांगा, मी त्यावरून पुढे जाईन."),
    "ambiguous": (  # {guess} is either empty or a short question naming the likely topics
        "I want to be sure I give you the right help, and I'm not fully sure what you need yet.{guess} Could you tell me a bit more, for example what you ordered and what went wrong?",
        "मैं आपको सही मदद देना चाहता हूँ, और अभी मुझे पूरी तरह पक्का नहीं है कि आपको क्या चाहिए।{guess} क्या आप थोड़ा और बता सकते हैं, जैसे आपने क्या ऑर्डर किया और क्या गड़बड़ हुई?",
        "আমি আপনাকে সঠিক সাহায্য দিতে চাই, আর এখনও পুরোপুরি নিশ্চিত নই আপনার কী দরকার।{guess} আরও একটু বলবেন কি, যেমন কী অর্ডার করেছিলেন এবং কী সমস্যা হয়েছে?",
        "உங்களுக்குச் சரியான உதவியை வழங்க விரும்புகிறேன், உங்களுக்கு என்ன தேவை என்று இன்னும் முழுமையாகத் தெரியவில்லை.{guess} கொஞ்சம் கூடுதலாகச் சொல்ல முடியுமா, உதாரணமாக என்ன ஆர்டர் செய்தீர்கள், என்ன தவறு நடந்தது?",
        "మీకు సరైన సహాయం అందించాలనుకుంటున్నాను, మీకు ఏమి కావాలో ఇంకా పూర్తిగా తెలియదు.{guess} దయచేసి కొంచెం ఎక్కువ చెప్పగలరా, ఉదాహరణకు ఏమి ఆర్డర్ చేశారు మరియు ఏమి తప్పు జరిగింది?",
        "मला तुम्हाला योग्य मदत करायची आहे, आणि तुम्हाला काय हवे आहे हे मला अजून पूर्णपणे समजलेले नाही.{guess} कृपया थोडे अधिक सांगाल का, उदाहरणार्थ तुम्ही काय ऑर्डर केले आणि काय चुकले?"),
    "guess1": (" Is this about **{a}**?", " क्या यह **{a}** के बारे में है?", " এটা কি **{a}** সম্পর্কে?", " இது **{a}** பற்றியதா?", " ఇది **{a}** గురించా?", " हे **{a}** बद्दल आहे का?"),
    "guess2": (" Is this about **{a}** or **{b}**?", " क्या यह **{a}** या **{b}** के बारे में है?", " এটা কি **{a}** নাকি **{b}** সম্পর্কে?", " இது **{a}** அல்லது **{b}** பற்றியதா?", " ఇది **{a}** లేదా **{b}** గురించా?", " हे **{a}** की **{b}** बद्दल आहे?"),
    "escalate": (  # {why} is one of the reasons below
        "I want to be sure you get the right help, so I'm recommending this for **human review**, because {why}. A support agent can verify your details and look into it. Nothing on your order, payment, refund or account has been changed.",
        "मैं चाहता हूँ कि आपको सही मदद मिले, इसलिए मैं इसे **मानव समीक्षा** के लिए सुझा रहा हूँ, क्योंकि {why}। सपोर्ट एजेंट आपकी जानकारी जाँचकर इसे देख सकता है। आपके ऑर्डर, भुगतान, रिफंड या खाते में कुछ भी नहीं बदला गया है।",
        "আমি চাই আপনি সঠিক সাহায্য পান, তাই এটি **মানুষের পর্যালোচনার** জন্য সুপারিশ করছি, কারণ {why}। একজন সাপোর্ট এজেন্ট আপনার তথ্য যাচাই করে বিষয়টি দেখতে পারবেন। আপনার অর্ডার, পেমেন্ট, রিফান্ড বা অ্যাকাউন্টে কিছুই পরিবর্তন করা হয়নি।",
        "உங்களுக்குச் சரியான உதவி கிடைக்க வேண்டும் என்பதால், இதை **மனித மதிப்பாய்வுக்கு** பரிந்துரைக்கிறேன், ஏனெனில் {why}. ஒரு ஆதரவு முகவர் உங்கள் விவரங்களைச் சரிபார்த்து இதைப் பார்க்க முடியும். உங்கள் ஆர்டர், கட்டணம், பணத்திரும்பப் பெறுதல் அல்லது கணக்கில் எதுவும் மாற்றப்படவில்லை.",
        "మీకు సరైన సహాయం అందాలని కోరుకుంటున్నాను, అందుకే దీన్ని **మానవ సమీక్ష**కు సిఫార్సు చేస్తున్నాను, ఎందుకంటే {why}. సపోర్ట్ ఏజెంట్ మీ వివరాలను ధృవీకరించి దీన్ని పరిశీలించగలరు. మీ ఆర్డర్, చెల్లింపు, రీఫండ్ లేదా ఖాతాలో ఏదీ మార్చబడలేదు.",
        "तुम्हाला योग्य मदत मिळावी म्हणून मी हे **मानवी पुनरावलोकनासाठी** सुचवत आहे, कारण {why}. सपोर्ट एजंट तुमचे तपशील तपासून हे पाहू शकतो. तुमच्या ऑर्डर, पेमेंट, परतावा किंवा खात्यात काहीही बदललेले नाही."),
}
A5_WHY = {   # English text (as written in agents_l2.ESC_TEXT) -> (hi, bn, ta, te, mr)
    "I couldn't work out what you need with enough confidence": (
        "मैं पर्याप्त भरोसे के साथ यह नहीं समझ पाया कि आपको क्या चाहिए", "আমি যথেষ্ট নিশ্চিত হয়ে বুঝতে পারিনি আপনার কী দরকার",
        "உங்களுக்கு என்ன தேவை என்பதை போதுமான நம்பிக்கையுடன் என்னால் புரிந்துகொள்ள முடியவில்லை", "మీకు ఏమి కావాలో తగినంత నమ్మకంతో నేను గుర్తించలేకపోయాను",
        "तुम्हाला काय हवे आहे हे मला पुरेशा खात्रीने समजले नाही"),
    "I don't have reliable guidance for this request": (
        "इस अनुरोध के लिए मेरे पास भरोसेमंद मार्गदर्शन नहीं है", "এই অনুরোধের জন্য আমার কাছে নির্ভরযোগ্য নির্দেশনা নেই",
        "இந்தக் கோரிக்கைக்கு என்னிடம் நம்பகமான வழிகாட்டுதல் இல்லை", "ఈ అభ్యర్థనకు నా దగ్గర నమ్మదగిన మార్గదర్శకం లేదు",
        "या विनंतीसाठी माझ्याकडे विश्वासार्ह मार्गदर्शन नाही"),
    "the guidance I found was contradictory and I couldn't resolve it": (
        "मुझे मिला मार्गदर्शन आपस में विरोधाभासी था और मैं उसे सुलझा नहीं पाया", "আমি যে নির্দেশনা পেয়েছি তা পরস্পরবিরোধী ছিল এবং আমি সমাধান করতে পারিনি",
        "எனக்குக் கிடைத்த வழிகாட்டுதல் முரண்பட்டதாக இருந்தது, அதை என்னால் தீர்க்க முடியவில்லை", "నాకు దొరికిన మార్గదర్శకం పరస్పర విరుద్ధంగా ఉంది, నేను దాన్ని పరిష్కరించలేకపోయాను",
        "मला मिळालेले मार्गदर्शन परस्परविरोधी होते आणि मी ते सोडवू शकलो नाही"),
    "I couldn't produce a response I can fully stand behind": (
        "मैं ऐसा उत्तर नहीं बना पाया जिस पर मैं पूरी तरह भरोसा कर सकूँ", "আমি এমন উত্তর তৈরি করতে পারিনি যার ওপর আমি পুরোপুরি ভরসা করতে পারি",
        "நான் முழுமையாக நம்பக்கூடிய பதிலை உருவாக்க முடியவில்லை", "నేను పూర్తిగా నమ్మగలిగే సమాధానాన్ని రూపొందించలేకపోయాను",
        "मी पूर्णपणे विश्वास ठेवू शकेन असे उत्तर तयार करू शकलो नाही"),
    "your request is still unclear after a follow-up question": (
        "अनुवर्ती प्रश्न के बाद भी आपका अनुरोध अस्पष्ट है", "ফলো-আপ প্রশ্নের পরেও আপনার অনুরোধ অস্পষ্ট",
        "தொடர் கேள்விக்குப் பிறகும் உங்கள் கோரிக்கை தெளிவாக இல்லை", "ఫాలో-అప్ ప్రశ్న తర్వాత కూడా మీ అభ్యర్థన అస్పష్టంగా ఉంది",
        "पाठपुरावा प्रश्नानंतरही तुमची विनंती अस्पष्ट आहे"),
    "I couldn't match this to an order": (
        "मैं इसे किसी ऑर्डर से नहीं जोड़ पाया", "আমি এটিকে কোনো অর্ডারের সঙ্গে মেলাতে পারিনি",
        "இதை எந்த ஆர்டருடனும் என்னால் பொருத்த முடியவில்லை", "దీన్ని ఏ ఆర్డర్‌తోనూ నేను సరిపోల్చలేకపోయాను",
        "मी हे कोणत्याही ऑर्डरशी जुळवू शकलो नाही"),
    "this needs a closer look": (
        "इसे और बारीकी से देखने की ज़रूरत है", "এটি আরও ভালোভাবে দেখা দরকার", "இதை இன்னும் நெருக்கமாகப் பார்க்க வேண்டும்",
        "దీన్ని మరింత నిశితంగా చూడాలి", "हे अधिक बारकाईने पाहण्याची गरज आहे"),
}

# --------------------------------------------------------------------------- translation backend
_cache = None
_status = {"live": None, "last_error": ""}      # live: None = untested, True = works, False = unavailable


def _load_cache():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _cache = {}
        except Exception:                               # unreadable file: keep a copy, never silently wipe it
            try:
                CACHE_FILE.replace(CACHE_FILE.with_suffix(".json.corrupt"))
            except Exception:
                pass
            _cache = {}
    return _cache


def _save_cache():
    try:                                                # write to a temp file, then swap: a crash cannot corrupt the cache
        tmp = CACHE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_cache, ensure_ascii=False, indent=0), encoding="utf-8")
        tmp.replace(CACHE_FILE)
    except Exception:
        pass


# Translation backends. GS_TRANSLATOR = auto (default: offline NLLB first, Google as fallback) | nllb | google
BACKEND = os.environ.get("GS_TRANSLATOR", "auto")
NLLB_MODEL = os.environ.get("GS_NLLB_MODEL", "facebook/nllb-200-distilled-600M")
NLLB_CODE = {"en": "eng_Latn", "hi": "hin_Deva", "bn": "ben_Beng", "ta": "tam_Taml", "te": "tel_Telu", "mr": "mar_Deva"}
_nllb = {}
_dead = set()                       # backends that cannot work on this machine: skipped after the first failure
_SENT = re.compile(r"(?<=[.!?\u0964])\s+")
_PREFIX = re.compile(r"^(\s*(?:[-*\u2022]|\d+[.)])\s+)")


def _script(text):
    """Which Indian script the text is written in (first non-Latin letter decides); 'en' if none."""
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            return "hi"
        if 0x0980 <= o <= 0x09FF:
            return "bn"
        if 0x0B80 <= o <= 0x0BFF:
            return "ta"
        if 0x0C00 <= o <= 0x0C7F:
            return "te"
    return "en"


def _nllb_load():
    if "model" not in _nllb:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer   # pip install transformers torch sentencepiece
            print("Loading the offline translation model (the first run downloads about 2.4 GB) ...", flush=True)
            _nllb["tok"] = AutoTokenizer.from_pretrained(NLLB_MODEL)
            _nllb["model"] = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL).eval()
        except Exception:
            _dead.add("nllb")
            raise
    return _nllb["tok"], _nllb["model"]


def _nllb_line(line, src, dst):
    """One line of text, sentence by sentence (the model works best on single sentences)."""
    import torch
    tok, model = _nllb_load()
    m = _PREFIX.match(line)
    prefix, body = (m.group(1), line[m.end():]) if m else ("", line.strip())
    sents = [x.strip() for x in _SENT.split(body) if x.strip()]
    if not sents:
        return line
    tok.src_lang = NLLB_CODE[src]
    outs = []
    for i in range(0, len(sents), 8):
        enc = tok(sents[i:i + 8], return_tensors="pt", padding=True, truncation=True, max_length=256)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(NLLB_CODE[dst]),
                                 num_beams=3, max_new_tokens=256)
        outs += tok.batch_decode(gen, skip_special_tokens=True)
    return prefix + " ".join(outs)


def _live_nllb(text, src, dst):
    """Offline machine translation (Meta NLLB-200). Keeps [[n]] placeholders and line breaks untouched."""
    if src == "auto":
        src = _script(text)
    elif src != "en" and _script(text) in ("bn", "ta", "te") and _script(text) != src:
        src = _script(text)                             # customer typed another script than the selected language
    if src not in NLLB_CODE or dst not in NLLB_CODE:
        raise ValueError(f"unsupported language pair {src}>{dst}")
    if src == dst:
        return text
    out = []
    for part in re.split(r"(\[\[\d+\]\])", text):
        if not part.strip() or re.fullmatch(r"\[\[\d+\]\]", part):
            out.append(part)
            continue
        lead, trail = part[:len(part) - len(part.lstrip())], part[len(part.rstrip()):]
        lines = part.strip().split("\n")
        out.append(lead + "\n".join(_nllb_line(l, src, dst) if l.strip() else l for l in lines) + trail)
    return "".join(out)


def _live_google(text, src, dst):
    from deep_translator import GoogleTranslator   # pip install deep-translator
    return GoogleTranslator(source=GOOGLE_CODE.get(src, src), target=GOOGLE_CODE.get(dst, dst)).translate(text)


def _live(text, src, dst):
    """One live machine translation. Raises when no backend works."""
    err = None
    for b in (["nllb", "google"] if BACKEND == "auto" else [BACKEND]):
        if b in _dead:
            continue
        try:
            out = _live_nllb(text, src, dst) if b == "nllb" else _live_google(text, src, dst)
            _status["backend"] = b
            return out
        except ImportError as e:                         # library not installed: do not try this backend again
            _dead.add(b)
            err = e
        except Exception as e:
            err = e
    raise err or RuntimeError("no translation backend available")


def _translate(text, src, dst):
    """Cached machine translation. Returns (translated_text, how) - how is cache / live / unavailable."""
    text = (text or "").strip()
    if not text or src == dst:
        return text, "same"
    cache = _load_cache()
    key = f"{src}>{dst}|{text}"
    if key in cache:
        return cache[key], "cache"
    if _status["live"] is False and time.time() - _status.get("t", 0) < 60:
        return text, "unavailable"                     # recently failed: do not make every call wait
    try:
        out = _live(text, src, dst)
        if out:
            cache[key] = out
            _save_cache()
            _status["live"] = True
            return out, "live"
    except Exception as e:                              # offline, library missing, rate limited ...
        _status.update(live=False, last_error=f"{type(e).__name__}: {e}"[:200], t=time.time())
    return text, "unavailable"


def status():
    return dict(_status)


def reset_backoff():
    """Forget a recent failure so the next call really tries the network (used by warm_translations.py retries)."""
    _status.update(live=None, t=0)


def is_rate_limited():
    """True when the last live failure looks like Google blocking us for sending too many requests."""
    e = (_status.get("last_error") or "").lower()
    return "toomanyrequests" in e or "too many" in e or "429" in e


# --------------------------------------------------------------------------- public API
def tr(text, lang, **fmt):
    """UI text in `lang`. Hand table first, then cached/live machine translation, then English."""
    out = text
    if lang != "en":
        row = UI.get(text)
        if row:
            out = row[ORDER.index(lang) - 1]
        else:
            out, _ = _translate(text, "en", lang)
    return out.format(**fmt) if fmt else out


def to_english(text, lang):
    """Customer text -> English for the agents. Returns (english, info).
    Text written only in Latin letters is passed through as English (this also covers a customer who types
    English while an Indian language is selected). Anything else is auto-detected and translated."""
    t0 = time.perf_counter()
    text = (text or "").strip()
    if not text:
        return text, {"how": "empty", "ms": 0.0}
    if text.isascii():
        return text, {"how": "english", "ms": 0.0}
    out, how = _translate(text, lang if (lang in LANGS and lang != "en") else "auto", "en")
    return out, {"how": how, "ms": round((time.perf_counter() - t0) * 1000, 1)}


def _protect(text):
    """Keep **bold** markers and {{placeholders}} intact through machine translation."""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"[[{len(keep) - 1}]]"
    return re.sub(r"\{\{[^}]*\}\}|\*\*", stash, text), keep


def _restore(text, keep):
    for i, k in enumerate(keep):
        text = re.sub(rf"\[\[\s*{i}\s*\]\]", lambda _m, k=k: k, text)
    return text


def mt(text, dst):
    """English -> dst machine translation with markdown protection. Returns (text, how)."""
    if dst == "en" or not text:
        return text, "same"
    safe, keep = _protect(text)
    out, how = _translate(safe, "en", dst)
    return (_restore(out, keep) if how != "unavailable" else text), how


def localize_response(res, lang):
    """The agents' reply (English) in `lang`. Returns (text, info).
    CLARIFY / ESCALATE use the hand-written A5 templates; ANSWER text uses machine translation."""
    t0 = time.perf_counter()
    en = res["final_response"]
    if lang == "en":
        return en, {"how": "english", "ms": 0.0}
    i = ORDER.index(lang)
    dec, reason = res["decision"], res["a5"]["reason"]
    how = "template"
    try:
        if dec == "ESCALATE":
            import agents_l2 as L2
            why_en = L2.ESC_TEXT.get(reason, "this needs a closer look")
            why = A5_WHY[why_en][i - 1] if why_en in A5_WHY else mt(why_en, lang)[0]
            out = A5["escalate"][i].format(why=why)
        elif dec == "CLARIFY" and reason == "missing_info":
            out = A5["missing"][i]
        elif dec == "CLARIFY":
            names = [str(c["intent"]).replace("_", " ") for c in res["a1"]["candidates"][:2] if float(c["prob"]) >= 0.1]
            names = [mt(n, lang)[0] for n in names]
            guess = (A5["guess2"][i].format(a=names[0], b=names[1]) if len(names) > 1 else
                     A5["guess1"][i].format(a=names[0]) if names else "")
            out = A5["ambiguous"][i].format(guess=guess)
        else:
            out, how = mt(en, lang)
    except Exception:
        out, how = en, "unavailable"
    return out, {"how": how, "ms": round((time.perf_counter() - t0) * 1000, 1)}


def add_language_steps(res, lang, original, english, in_info, local, out_info):
    """Write the two translation steps into the agent trace (first and last) and keep the texts on `res`."""
    res["language"] = {"selected": lang, "original_query": original, "english_query": english,
                       "reply_local": local, "translate_in": in_info, "translate_out": out_info}
    first = {"agent": "Lang", "role": "Language layer: translate in", "inputs": {"text": original, "language": lang},
             "outputs": {"english": english}, "decision": f"{lang}→en ({in_info['how']})", "evidence": [], "ms": in_info["ms"]}
    last = {"agent": "Lang", "role": "Language layer: translate out", "inputs": {"english_reply": res["final_response"]},
            "outputs": {"reply": local, "language": lang}, "decision": f"en→{lang} ({out_info['how']})", "evidence": [], "ms": out_info["ms"]}
    if lang != "en":                      # English chats keep the original five-agent trace untouched
        res["trace"] = [first] + list(res["trace"]) + [last]
    return res


def language_notice(lang):
    """A short message for the UI when live translation is not available (None when everything is fine)."""
    if lang != "en" and _status["live"] is False:
        return ("Live translation is not available right now (offline, or `deep-translator` is not installed), "
                "so replies may show in English. Menus and follow-up questions still work.")
    return None


def ui_dict(lang, keys, **fmt):
    """{english: translated} for a list of keys - used to hand the dashboard (home.html) its labels."""
    return {k: tr(k, lang, **fmt) for k in keys}


if __name__ == "__main__":     # python lang.py  -> quick self-check
    missing = [k for k, v in UI.items() if len(v) != 5]
    print("UI strings:", len(UI), "| rows with the wrong number of columns:", missing or "none")
    print("A5 templates:", {k: len(v) for k, v in A5.items()}, "| reasons:", len(A5_WHY))
    for lg in ORDER:
        print(lg, LANGS[lg][0], "|", tr("+ New chat", lg), "|", tr("{store} support", lg, store="Amazon"))
