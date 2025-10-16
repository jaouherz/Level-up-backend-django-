import os
import json
import time
from dotenv import load_dotenv
from groq import Groq
from api.models import Certification, Skill

# -----------------------------------------------------
# 1️⃣ CONFIGURATION
# -----------------------------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env file")

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.1-8b-instant"

# -----------------------------------------------------
# 2️⃣ LLM LOGIC
# -----------------------------------------------------
def ask_groq_for_related_skills(cert_name, skills):
    """
    Uses LLaMA 3 via Groq to detect which skills are relevant to a certification.
    Returns a list of matching skill names.
    """
    prompt = f"""
You are an AI expert in IT certifications and skill matching.
Certification: "{cert_name}"
Skill options: {', '.join(skills)}

Identify which of these skills are directly relevant to the certification.
Return ONLY a valid JSON array of skill names, example:
["Python", "Machine Learning"]
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a precise IT skill matcher."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        text = response.choices[0].message.content.strip()
        start, end = text.find('['), text.rfind(']') + 1
        if start != -1 and end != -1:
            json_text = text[start:end]
            parsed = json.loads(json_text)
            valid_skills = [s for s in parsed if s in skills]
            return valid_skills
        else:
            print(f"⚠️ Could not parse response for '{cert_name}': {text}")
            return []

    except Exception as e:
        print(f"❌ Groq API error for '{cert_name}': {e}")
        return []

# -----------------------------------------------------
# 3️⃣ MAIN AUTO-LINK FUNCTION
# -----------------------------------------------------
def auto_link_certifications():
    """
    For each Certification in DB:
    → Ask Groq which skills match
    → Link them automatically to the certification
    """
    all_skills = list(Skill.objects.values_list("name", flat=True))
    certifications = Certification.objects.all()

    if not certifications.exists():
        print("⚠️ No certifications found in database.")
        return

    summary = []

    for cert in certifications:
        print(f"\n🔍 Analyzing certification: {cert.name}")
        matched_skills = ask_groq_for_related_skills(cert.name, all_skills)

        if matched_skills:
            cert.skills.set(Skill.objects.filter(name__in=matched_skills))
            cert.save()
            summary.append((cert.name, matched_skills))
            print(f"✅ Linked {len(matched_skills)} skill(s): {matched_skills}")
        else:
            print(f"⚠️ No related skills found for '{cert.name}'")

        time.sleep(0.5)  # Respect rate limits

    print("\n🏁 Done linking all certifications!\n")
    print("📊 Summary:")
    for cert_name, skills in summary:
        print(f"  {cert_name} → {', '.join(skills)}")

# -----------------------------------------------------
# 4️⃣ MANUAL TEST MODE
# -----------------------------------------------------
if __name__ == "__main__":
    print("🚀 Running Groq certification-skill auto-linker...\n")
    auto_link_certifications()
