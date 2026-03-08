"""Trilingual SMS/notification templates for VaaniSetu."""

# ── Application Submission Confirmation ───────────────────────────────

APPLICATION_SUBMITTED = {
    "hi-IN": (
        "✅ वाणी सेतु — आवेदन जमा!\n\n"
        "योजना: {scheme_name}\n"
        "आवेदन ID: {application_id}\n"
        "तारीख: {date}\n\n"
        "स्थिति: प्राप्त हुआ\n"
        "अनुमानित समय: {processing_time}\n\n"
        "आप अपने आवेदन की स्थिति जानने के लिए वाणी सेतु पर +91-{helpline} पर कॉल कर सकते हैं।"
    ),
    "en-IN": (
        "✅ VaaniSetu — Application Submitted!\n\n"
        "Scheme: {scheme_name}\n"
        "Application ID: {application_id}\n"
        "Date: {date}\n\n"
        "Status: Received\n"
        "Estimated time: {processing_time}\n\n"
        "Call VaaniSetu at +91-{helpline} to check your application status."
    ),
    "ta-IN": (
        "✅ வாணி சேது — விண்ணப்பம் சமர்ப்பிக்கப்பட்டது!\n\n"
        "திட்டம்: {scheme_name}\n"
        "விண்ணப்ப ID: {application_id}\n"
        "தேதி: {date}\n\n"
        "நிலை: பெறப்பட்டது\n"
        "மதிப்பிடப்பட்ட நேரம்: {processing_time}\n\n"
        "உங்கள் விண்ணப்ப நிலையை அறிய +91-{helpline} இல் VaaniSetu ஐ அழைக்கவும்."
    ),
}

# ── Status Update ─────────────────────────────────────────────────────

APPLICATION_STATUS_UPDATE = {
    "hi-IN": (
        "🔔 वाणी सेतु — स्थिति अपडेट\n\n"
        "आवेदन ID: {application_id}\n"
        "योजना: {scheme_name}\n"
        "नई स्थिति: {status}\n\n"
        "{status_message}"
    ),
    "en-IN": (
        "🔔 VaaniSetu — Status Update\n\n"
        "Application ID: {application_id}\n"
        "Scheme: {scheme_name}\n"
        "New Status: {status}\n\n"
        "{status_message}"
    ),
    "ta-IN": (
        "🔔 வாணி சேது — நிலை புதுப்பிப்பு\n\n"
        "விண்ணப்ப ID: {application_id}\n"
        "திட்டம்: {scheme_name}\n"
        "புதிய நிலை: {status}\n\n"
        "{status_message}"
    ),
}

# ── Scheme Match Notification ─────────────────────────────────────────

SCHEME_MATCH = {
    "hi-IN": (
        "🎯 वाणी सेतु — योजना मिली!\n\n"
        "आपकी प्रोफ़ाइल के आधार पर, आप इन योजनाओं के लिए पात्र हो सकते हैं:\n\n"
        "{schemes_list}\n\n"
        "अधिक जानने के लिए वाणी सेतु से बात करें।"
    ),
    "en-IN": (
        "🎯 VaaniSetu — Schemes Found!\n\n"
        "Based on your profile, you may be eligible for:\n\n"
        "{schemes_list}\n\n"
        "Talk to VaaniSetu to learn more."
    ),
    "ta-IN": (
        "🎯 வாணி சேது — திட்டங்கள் கண்டறியப்பட்டன!\n\n"
        "உங்கள் சுயவிவரத்தின் அடிப்படையில், நீங்கள் தகுதி பெறலாம்:\n\n"
        "{schemes_list}\n\n"
        "மேலும் அறிய VaaniSetu உடன் பேசுங்கள்."
    ),
}

# ── Documents Needed Reminder ─────────────────────────────────────────

DOCUMENTS_NEEDED = {
    "hi-IN": (
        "📋 वाणी सेतु — दस्तावेज़ आवश्यक\n\n"
        "योजना: {scheme_name}\n\n"
        "कृपया ये दस्तावेज़ तैयार रखें:\n"
        "{documents_list}\n\n"
        "आवेदन पूरा करने के लिए वाणी सेतु से बात करें।"
    ),
    "en-IN": (
        "📋 VaaniSetu — Documents Needed\n\n"
        "Scheme: {scheme_name}\n\n"
        "Please keep these documents ready:\n"
        "{documents_list}\n\n"
        "Talk to VaaniSetu to complete your application."
    ),
    "ta-IN": (
        "📋 வாணி சேது — ஆவணங்கள் தேவை\n\n"
        "திட்டம்: {scheme_name}\n\n"
        "இந்த ஆவணங்களை தயாராக வைத்திருக்கவும்:\n"
        "{documents_list}\n\n"
        "விண்ணப்பத்தை முடிக்க VaaniSetu உடன் பேசுங்கள்."
    ),
}

# ── Welcome / OTP ─────────────────────────────────────────────────────

WELCOME = {
    "hi-IN": "🙏 वाणी सेतु में आपका स्वागत है! सरकारी योजनाओं के बारे में बात करने के लिए कॉल करें। हमारा नंबर: +91-{helpline}",
    "en-IN": "🙏 Welcome to VaaniSetu! Call us to learn about government schemes. Our number: +91-{helpline}",
    "ta-IN": "🙏 வாணி சேது க்கு வரவேற்கிறோம்! அரசு திட்டங்களைப் பற்றி அறிய எங்களை அழைக்கவும்: +91-{helpline}",
}

# ── Status Messages (for status update template) ─────────────────────

STATUS_MESSAGES = {
    "pending": {
        "hi-IN": "आपका आवेदन समीक्षा के लिए कतार में है।",
        "en-IN": "Your application is in the review queue.",
        "ta-IN": "உங்கள் விண்ணப்பம் மதிப்பாய்வு வரிசையில் உள்ளது.",
    },
    "under_review": {
        "hi-IN": "आपका आवेदन वर्तमान में समीक्षा में है।",
        "en-IN": "Your application is currently under review.",
        "ta-IN": "உங்கள் விண்ணப்பம் தற்போது மதிப்பாய்வில் உள்ளது.",
    },
    "approved": {
        "hi-IN": "🎉 बधाई! आपका आवेदन स्वीकृत हो गया है। लाभ जल्द ही प्राप्त होगा।",
        "en-IN": "🎉 Congratulations! Your application has been approved. Benefits will be disbursed soon.",
        "ta-IN": "🎉 வாழ்த்துக்கள்! உங்கள் விண்ணப்பம் அங்கீகரிக்கப்பட்டது. நன்மைகள் விரைவில் வழங்கப்படும்.",
    },
    "rejected": {
        "hi-IN": "❌ दुर्भाग्यवश आपका आवेदन अस्वीकृत हो गया है। कारण जानने के लिए वाणी सेतु पर कॉल करें।",
        "en-IN": "❌ Unfortunately your application was rejected. Call VaaniSetu to learn the reason.",
        "ta-IN": "❌ துரதிர்ஷ்டவசமாக உங்கள் விண்ணப்பம் நிராகரிக்கப்பட்டது. காரணத்தை அறிய VaaniSetu ஐ அழைக்கவும்.",
    },
}

# ── Helpline number placeholder ───────────────────────────────────────
DEFAULT_HELPLINE = "1800XXXX"

DEFAULT_PROCESSING_TIME = {
    "hi-IN": "7-15 कार्यदिवस",
    "en-IN": "7-15 business days",
    "ta-IN": "7-15 வணிக நாட்கள்",
}


def get_template(template_name: str, language: str = "hi-IN", **kwargs) -> str:
    """
    Get a formatted notification template.

    Args:
        template_name: One of APPLICATION_SUBMITTED, APPLICATION_STATUS_UPDATE, etc.
        language: Language code (hi-IN, en-IN, ta-IN)
        **kwargs: Template variables

    Returns:
        Formatted SMS text
    """
    templates = {
        "application_submitted": APPLICATION_SUBMITTED,
        "status_update": APPLICATION_STATUS_UPDATE,
        "scheme_match": SCHEME_MATCH,
        "documents_needed": DOCUMENTS_NEEDED,
        "welcome": WELCOME,
    }

    template_dict = templates.get(template_name.lower())
    if not template_dict:
        return f"VaaniSetu notification: {template_name}"

    text = template_dict.get(language, template_dict.get("hi-IN", ""))

    # Fill defaults
    kwargs.setdefault("helpline", DEFAULT_HELPLINE)
    kwargs.setdefault("processing_time", DEFAULT_PROCESSING_TIME.get(language, "7-15 days"))

    # Fill status message
    if "status" in kwargs and template_name.lower() == "status_update":
        status = kwargs["status"]
        status_msg_dict = STATUS_MESSAGES.get(status, {})
        kwargs["status_message"] = status_msg_dict.get(language, "")

    try:
        return text.format(**kwargs)
    except KeyError as e:
        return text  # Return unformatted if missing variables
