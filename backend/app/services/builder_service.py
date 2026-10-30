import io
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from app.models.builder_schemas import (
    TargetMode,
    ContactInfo,
    ExperienceItem,
    ProjectItem,
    EducationItem,
    StructuredResume,
    RequirementGapItem,
    ProposedChange,
    TargetedAnalysisResponse,
)
from app.services.synonyms import DEFAULT_SYNONYM_MAP, find_term_in_text, normalize_text
from app.services.parser import SECTION_PATTERNS, extract_job_requirements, ACTION_VERBS
from app.services.assistant import analyze_bullet_point


def segment_sections_preserving_case(text: str) -> Dict[str, str]:
    """
    Identifies and segments resume sections while preserving original letter casing
    for accurate entity extraction (names, company names, degrees, and bullets).
    """
    positions: List[Tuple[int, str]] = []
    for sec_name, pattern in SECTION_PATTERNS.items():
        for m in pattern.finditer(text):
            positions.append((m.start(), sec_name))

    positions.sort(key=lambda x: x[0])

    sections: Dict[str, str] = {}
    if not positions:
        sections["general"] = text
        return sections

    if positions[0][0] > 0:
        sections["header"] = text[:positions[0][0]].strip()

    for i in range(len(positions)):
        start_idx = positions[i][0]
        sec_name = positions[i][1]
        end_idx = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections[sec_name] = text[start_idx:end_idx].strip()

    return sections

# =============================================================================
# Role and Company Knowledge Profiles
# =============================================================================

COMPANY_PROFILES: Dict[str, Dict[str, Any]] = {
    "Google": {
        "culture_headline": "Engineering at Scale & Algorithmic Rigor",
        "key_focus_areas": [
            "Massive distributed systems and scalability",
            "Algorithmic efficiency, computational complexity, and data structures",
            "High test coverage, automated testing gates, and code maintainability",
            "Data-driven engineering outcomes (latency, throughput, resource usage)",
        ],
        "keywords": ["distributed systems", "concurrency", "scalability", "microservices", "optimization", "unit testing"],
    },
    "Amazon": {
        "culture_headline": "Customer Obsession & Operational Excellence",
        "key_focus_areas": [
            "High availability, fault tolerance, and disaster recovery",
            "Concrete business metrics: cost reduction, latency improvement, user adoption",
            "End-to-end ownership from design to on-call production monitoring",
            "Service-oriented architecture and cloud-native services (AWS)",
        ],
        "keywords": ["aws", "cloud", "scalability", "reliability", "cost optimization", "metrics", "microservices"],
    },
    "Meta": {
        "culture_headline": "High-Velocity Product Impact & Massive Traffic",
        "key_focus_areas": [
            "Fast iterative development, continuous deployment, and A/B testing",
            "High concurrency supporting billions of daily active interactions",
            "Full-stack product intuition and cross-functional feature execution",
            "API design efficiency and minimal network overhead",
        ],
        "keywords": ["react", "graphql", "rest api", "ci/cd", "scalability", "distributed systems", "python"],
    },
    "Apple": {
        "culture_headline": "Precision, Quality Craftsmanship & Performance",
        "key_focus_areas": [
            "System reliability, memory efficiency, and battery/resource impact",
            "Privacy by design and robust security architectures",
            "High UX polish, responsiveness, and resilient edge execution",
            "Thorough integration testing and defect prevention",
        ],
        "keywords": ["security", "performance", "optimization", "unit testing", "ci/cd", "quality"],
    },
    "Netflix": {
        "culture_headline": "High Autonomy, Resilience & Cloud Microservices",
        "key_focus_areas": [
            "Chaos engineering, fault isolation, and circuit breaking",
            "Real-time streaming, telemetry, and distributed caching",
            "Event-driven architectures (Kafka, message queues)",
            "Observability, proactive monitoring, and self-healing systems",
        ],
        "keywords": ["microservices", "cloud", "kafka", "redis", "resilience", "aws", "docker", "kubernetes"],
    },
    "Microsoft": {
        "culture_headline": "Enterprise Scale, Cloud Architecture & Integration",
        "key_focus_areas": [
            "Enterprise reliability, multi-tenant cloud systems, and security",
            "API backward compatibility and extensible developer frameworks",
            "Cross-platform tooling, Azure cloud ecosystem, and CI/CD automation",
            "Collaborative engineering and robust documentation standards",
        ],
        "keywords": ["azure", ".net", "cloud", "rest api", "docker", "kubernetes", "sql", "security", "ci/cd"],
    },
}

ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "sdet": {
        "canonical_title": "SDET / QA Automation Engineer",
        "essential_skills": ["python", "unit testing", "rest api", "ci/cd", "sql", "git", "docker"],
        "recommended_skills": ["playwright", "selenium", "pytest", "postman", "jenkins", "kubernetes", "performance testing"],
        "evaluation_criteria": [
            "Programming language proficiency (Python, Java, TypeScript)",
            "Automated test framework design (Pytest, Playwright, Selenium)",
            "REST API testing and validation (payloads, status codes, contract testing)",
            "CI/CD pipeline test integration and automated regression gates",
            "Database verification and SQL querying",
            "Root-cause debugging and defect lifecycle management",
            "Test strategy, code coverage elevation, and measurable quality metrics",
        ],
    },
    "qa automation": {
        "canonical_title": "QA Automation Engineer",
        "essential_skills": ["python", "unit testing", "rest api", "ci/cd", "sql", "git"],
        "recommended_skills": ["pytest", "selenium", "playwright", "postman", "docker"],
        "evaluation_criteria": [
            "Automation framework development and maintenance",
            "End-to-end web and API automated test suites",
            "CI/CD regression execution and build health monitoring",
            "Defect analysis and actionable bug reporting",
            "Quantified quality impact (test execution time reduction, defect escape reduction)",
        ],
    },
    "software engineer": {
        "canonical_title": "Software Engineer",
        "essential_skills": ["python", "sql", "git", "rest api", "ci/cd", "docker"],
        "recommended_skills": ["fastapi", "react", "typescript", "kubernetes", "aws", "unit testing"],
        "evaluation_criteria": [
            "End-to-end feature architecture and clean coding standards",
            "REST API design and asynchronous request handling",
            "Database schema modeling and query optimization",
            "Unit and integration test suites reaching high coverage",
            "Containerization and automated deployment",
        ],
    },
    "backend": {
        "canonical_title": "Backend Engineer",
        "essential_skills": ["python", "fastapi", "sql", "postgresql", "rest api", "git", "docker"],
        "recommended_skills": ["redis", "kafka", "kubernetes", "microservices", "aws", "ci/cd"],
        "evaluation_criteria": [
            "Scalable microservices backend architecture",
            "High concurrency, caching strategies (Redis), and connection pooling",
            "Relational database design and query execution profiling",
            "Message broker integration (Kafka, RabbitMQ)",
            "Container orchestration and cloud deployment",
        ],
    },
    "data analyst": {
        "canonical_title": "Data Analyst",
        "essential_skills": ["sql", "python", "excel", "tableau", "git"],
        "recommended_skills": ["power bi", "data science", "postgresql", "mysql"],
        "evaluation_criteria": [
            "Complex SQL data extraction and aggregation queries",
            "Data wrangling and statistical analysis with Python",
            "Executive business intelligence dashboards (Tableau, Power BI)",
            "Translating business requirements into actionable quantitative metrics",
        ],
    },
    "frontend": {
        "canonical_title": "Frontend Engineer",
        "essential_skills": ["javascript", "typescript", "react", "html", "css", "git"],
        "recommended_skills": ["node.js", "unit testing", "rest api", "ci/cd"],
        "evaluation_criteria": [
            "Modern component architecture and state management",
            "Web performance, core web vitals, and bundle size reduction",
            "Responsive layout across mobile, tablet, and desktop viewports",
            "Cross-browser compatibility and accessibility (WCAG)",
        ],
    },
    "devops": {
        "canonical_title": "DevOps / SRE Engineer",
        "essential_skills": ["docker", "kubernetes", "ci/cd", "linux", "git", "aws"],
        "recommended_skills": ["terraform", "devops", "python", "azure", "gcp"],
        "evaluation_criteria": [
            "Infrastructure as Code (Terraform, CloudFormation)",
            "Automated multi-stage CI/CD pipelines",
            "Container orchestration and service discovery",
            "System observability, alerting, and SLA/SLO uptime tracking",
        ],
    },
}


def match_role_profile(job_title: str) -> Dict[str, Any]:
    """Matches a job title string to the closest role profile or returns a general default."""
    jt_lower = job_title.lower()
    if "sdet" in jt_lower:
        return ROLE_PROFILES["sdet"]
    elif "qa" in jt_lower or "test" in jt_lower or "quality" in jt_lower:
        return ROLE_PROFILES["qa automation"]
    elif "backend" in jt_lower or "server" in jt_lower:
        return ROLE_PROFILES["backend"]
    elif "data" in jt_lower or "analyst" in jt_lower or "bi" in jt_lower:
        return ROLE_PROFILES["data analyst"]
    elif "frontend" in jt_lower or "ui" in jt_lower or "web" in jt_lower:
        return ROLE_PROFILES["frontend"]
    elif "devops" in jt_lower or "sre" in jt_lower or "cloud" in jt_lower or "infrastructure" in jt_lower:
        return ROLE_PROFILES["devops"]
    else:
        return ROLE_PROFILES["software engineer"]


# =============================================================================
# Resume Text Parser into StructuredResume
# =============================================================================

def parse_text_to_structured_resume(resume_text: str) -> StructuredResume:
    """
    Parses unstructured resume text into a structured, editable resume object.
    Preserves candidate's real personal details, jobs, dates, and bullets.
    """
    sections = segment_sections_preserving_case(resume_text)
    norm = normalize_text(resume_text)
    lines = [line.strip() for line in resume_text.split("\n") if line.strip()]

    # 1. Contact Information
    contact = ContactInfo()
    if lines:
        first_line = lines[0]
        # Clean potential title suffixes from name line e.g. "Alex Morgan - Senior Software Engineer"
        name_match = re.split(r"[-–|•:]", first_line)
        if name_match and len(name_match[0].strip().split()) <= 4:
            contact.full_name = name_match[0].strip()

    # Extract email
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", resume_text)
    if email_match:
        contact.email = email_match.group(0)

    # Extract phone
    phone_label_match = re.search(r"(?:Phone|Tel|Mobile|Cell):\s*([0-9\-\+\(\)\s.]+)", resume_text, re.IGNORECASE)
    if phone_label_match:
        contact.phone = phone_label_match.group(1).strip()
    else:
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", resume_text)
        if phone_match:
            contact.phone = phone_match.group(0).strip()

    # Extract location (heuristic: city/state/remote)
    loc_match = re.search(r"\b(?:Location:\s*|Lives\s+in\s*)([A-Za-z\s,]+)\b", resume_text, re.IGNORECASE)
    if loc_match:
        contact.location = loc_match.group(1).strip()
    elif "remote" in norm:
        contact.location = "Remote"

    # Extract LinkedIn / GitHub handles or URLs
    li_match = re.search(r"(?:linkedin\.com/in/|linkedin:\s*)([a-zA-Z0-9_\-]+)", resume_text, re.IGNORECASE)
    if li_match:
        contact.linkedin = f"linkedin.com/in/{li_match.group(1)}"

    gh_match = re.search(r"(?:github\.com/|github:\s*)([a-zA-Z0-9_\-]+)", resume_text, re.IGNORECASE)
    if gh_match:
        contact.github = f"github.com/{gh_match.group(1)}"

    # 2. Professional Summary
    summary_text = ""
    if "summary" in sections:
        # Strip header keyword
        summary_clean = re.sub(r"^(?:professional\s+summary|summary|profile|about\s+me)\b", "", sections["summary"], flags=re.IGNORECASE).strip()
        summary_text = summary_clean
    elif "header" in sections:
        # If text before first section exists, check if it contains a short summary
        header_lines = [l for l in sections["header"].split("\n") if len(l.split()) > 5]
        if header_lines:
            summary_text = " ".join(header_lines)

    # 3. Categorized Skills
    skills_dict: Dict[str, List[str]] = {
        "Languages": [],
        "Frameworks & Libraries": [],
        "Cloud, Tools & Databases": [],
        "Testing & Methodologies": [],
    }

    # Group recognized skills into standard ATS clusters
    skill_clusters = {
        "Languages": ["python", "javascript", "typescript", "golang", "c++", "c#", "sql", "html", "css"],
        "Frameworks & Libraries": ["fastapi", "react", "django", "flask", "node.js", "vue.js", "angular", "spring boot", ".net"],
        "Cloud, Tools & Databases": ["postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws", "gcp", "azure", "git", "kafka", "linux", "terraform"],
        "Testing & Methodologies": ["unit testing", "ci/cd", "microservices", "rest api", "agile", "devops", "tableau", "power bi", "excel", "data science"],
    }

    skills_text = sections.get("skills", "") + " " + resume_text
    skills_norm = normalize_text(skills_text)
    for cat, items in skill_clusters.items():
        found = []
        for item in items:
            matched, _ = find_term_in_text(item, skills_norm)
            if matched:
                found.append(item)
        skills_dict[cat] = sorted(found)

    # 4. Work Experience Items
    experience_items: List[ExperienceItem] = []
    exp_text = sections.get("experience", "")
    if exp_text:
        # Split into probable position blocks
        exp_lines = [l.strip() for l in exp_text.split("\n") if l.strip()]
        current_exp: Optional[ExperienceItem] = None
        current_bullets: List[str] = []

        for line in exp_lines:
            # Check if line looks like a job header (e.g. "Senior Engineer - TechCorp (2021 - Present)")
            date_match = re.search(r"\((?:\d{4}|present|current).*?\)", line, re.IGNORECASE) or re.search(r"\b(?:20\d\d|19\d\d)\s*[-–]\s*(?:20\d\d|present|current)\b", line, re.IGNORECASE)
            is_bullet = bool(re.match(r"^[-*•–—\d.)]+\s+", line))

            if date_match and not is_bullet:
                # Save previous experience
                if current_exp:
                    current_exp.bullets = current_bullets
                    experience_items.append(current_exp)
                    current_bullets = []

                # Parse title, company, dates
                date_str = date_match.group(0).strip("()")
                rest_line = line.replace(date_match.group(0), "").strip(" -–,|()")
                parts = re.split(r"[-–|@]", rest_line)
                title = parts[0].strip() if parts else "Software Engineer"
                company = parts[1].strip() if len(parts) > 1 else "Technology Company"

                current_exp = ExperienceItem(
                    id=f"exp-{len(experience_items) + 1}",
                    title=title or "Software Engineer",
                    company=company or "Company",
                    start_date=date_str.split("-")[0].strip() if "-" in date_str else date_str,
                    end_date=date_str.split("-")[-1].strip() if "-" in date_str else "Present",
                    bullets=[],
                )
            elif is_bullet:
                clean_b = re.sub(r"^[-*•–—\d.)]+\s*", "", line).strip()
                if clean_b and len(clean_b) > 15:
                    current_bullets.append(clean_b)
            elif current_exp and len(line) > 25 and not line.lower().startswith("work experience"):
                current_bullets.append(line)

        if current_exp:
            current_exp.bullets = current_bullets
            experience_items.append(current_exp)

    # Fallback if no structured experience was parsed
    if not experience_items:
        raw_bullets = [re.sub(r"^[-*•–—\d.)]+\s*", "", l).strip() for l in lines if l.startswith(("-", "*", "•"))]
        if raw_bullets:
            experience_items.append(
                ExperienceItem(
                    id="exp-1",
                    title="Professional Experience",
                    company="Previous Employer",
                    bullets=raw_bullets[:6],
                )
            )

    # 5. Education
    education_items: List[EducationItem] = []
    edu_text = sections.get("education", "")
    if edu_text:
        edu_lines = [l.strip() for l in edu_text.split("\n") if l.strip()]
        for line in edu_lines:
            if any(deg in line.lower() for deg in ["bachelor", "master", "ph.d", "b.s", "m.s", "degree", "diploma", "b.tech"]):
                deg_match = re.split(r"[-–|,]", line)
                degree = deg_match[0].strip()
                inst = deg_match[1].strip() if len(deg_match) > 1 else "University"
                year_match = re.search(r"\b(20\d\d|19\d\d)\b", line)
                education_items.append(
                    EducationItem(
                        id=f"edu-{len(education_items) + 1}",
                        degree=degree,
                        institution=inst,
                        graduation_date=year_match.group(0) if year_match else None,
                    )
                )

    if not education_items:
        # Default placeholder if none found
        education_items.append(
            EducationItem(
                id="edu-1",
                degree="Bachelor of Science in Computer Science or Related Field",
                institution="Accredited University",
                graduation_date=None,
            )
        )

    # 6. Projects & Certifications
    projects: List[ProjectItem] = []
    if "projects" in sections:
        proj_lines = [l.strip() for l in sections["projects"].split("\n") if l.strip()]
        proj_bullets = [re.sub(r"^[-*•–—\d.)]+\s*", "", l).strip() for l in proj_lines if l.startswith(("-", "*", "•"))]
        if proj_bullets:
            projects.append(
                ProjectItem(
                    id="proj-1",
                    title="Key Technical Project",
                    technologies=skills_dict["Languages"][:3] + skills_dict["Frameworks & Libraries"][:2],
                    bullets=proj_bullets[:3],
                )
            )

    certifications: List[str] = []
    if "certifications" in sections:
        cert_lines = [re.sub(r"^[-*•–—\d.)]+\s*", "", l).strip() for l in sections["certifications"].split("\n") if l.strip() and not l.lower().startswith("certification")]
        certifications = cert_lines[:4]

    return StructuredResume(
        contact_info=contact,
        summary=summary_text or "Results-driven engineering professional with hands-on experience developing robust software solutions.",
        skills=skills_dict,
        experience=experience_items,
        projects=projects,
        education=education_items,
        certifications=certifications,
    )


# =============================================================================
# Targeted Analysis and Gap Assessment Engine
# =============================================================================

def analyze_targeted_resume(
    resume_text: str,
    target_mode: TargetMode,
    company_name: str,
    job_title: str,
    industry: Optional[str] = None,
    job_description: Optional[str] = "",
    sections_to_improve: Optional[List[str]] = None,
) -> TargetedAnalysisResponse:
    """
    Analyzes resume against the target company and role.
    Strict Priority:
    1. Actual user-supplied Job Description
    2. Company & Role Guidance
    3. General Role-Specific Guidance
    """
    if sections_to_improve is None:
        sections_to_improve = ["summary", "skills", "experience", "projects"]

    norm_resume = normalize_text(resume_text)
    has_jd = bool(job_description and len(job_description.strip().split()) >= 5)

    # Determine guidance source
    if has_jd:
        guidance_source = "Actual Job Description (Primary Source)"
    elif target_mode == TargetMode.FAANG_BIG_TECH and company_name in COMPANY_PROFILES:
        guidance_source = f"{company_name} Engineering Culture & Role Guidance"
    else:
        guidance_source = f"General Role-Specific Guidance for {job_title}"

    # Target skills extraction
    target_skills: Set[str] = set()
    mandatory_reqs: List[str] = []
    preferred_reqs: List[str] = []

    role_profile = match_role_profile(job_title)

    if has_jd:
        parsed_jd = extract_job_requirements(job_description)
        target_skills.update(parsed_jd.get("job_skills", []))
        mandatory_reqs = parsed_jd.get("mandatory_requirements", [])
        preferred_reqs = parsed_jd.get("preferred_requirements", [])
    else:
        # Use role and company profiles
        target_skills.update(role_profile["essential_skills"])
        target_skills.update(role_profile["recommended_skills"])
        if company_name in COMPANY_PROFILES:
            target_skills.update(COMPANY_PROFILES[company_name]["keywords"])

    # Evaluate matches, missing, and weakly evidenced
    matched_skills: List[RequirementGapItem] = []
    missing_requirements: List[RequirementGapItem] = []
    weakly_evidenced: List[RequirementGapItem] = []

    sections = segment_sections_preserving_case(resume_text)
    exp_text = sections.get("experience", "").lower()

    for skill in sorted(list(target_skills)):
        matched, matched_term = find_term_in_text(skill, norm_resume)
        if matched:
            in_experience = skill in exp_text
            if in_experience:
                matched_skills.append(
                    RequirementGapItem(
                        name=skill,
                        category="skill",
                        status="matched",
                        reason=f"Skill '{skill}' is well-evidenced with practical context in your experience section.",
                        evidence_source=guidance_source,
                        actionable_guidance="Maintain strong quantifiable metrics highlighting this skill.",
                        requires_user_confirmation=False,
                    )
                )
            else:
                weakly_evidenced.append(
                    RequirementGapItem(
                        name=skill,
                        category="skill",
                        status="weakly_evidenced",
                        reason=f"Skill '{skill}' is listed in your resume but lacks concrete accomplishment bullet points in Work Experience.",
                        evidence_source=guidance_source,
                        actionable_guidance=f"Add a project or work experience bullet illustrating how you deployed '{skill}' in production.",
                        requires_user_confirmation=False,
                    )
                )
        else:
            missing_requirements.append(
                RequirementGapItem(
                    name=skill,
                    category="skill",
                    status="missing",
                    reason=f"Skill '{skill}' is expected for {job_title} at {company_name} but is not found in your resume.",
                    evidence_source=guidance_source,
                    actionable_guidance=(
                        f"If you have genuine experience with '{skill}', confirm and add it to your Skills and Work Experience sections. "
                        "If you do NOT possess this skill, do not fabricate it; highlight related transferable background."
                    ),
                    requires_user_confirmation=True,
                )
            )

    # Parse raw text to structured resume
    structured_resume = parse_text_to_structured_resume(resume_text)

    # Generate Proposed Rewrites
    proposed_changes: List[ProposedChange] = []
    change_counter = 1

    # 1. Summary Upgrade
    if "summary" in sections_to_improve:
        years_exp = len(structured_resume.experience) * 2 or 3
        top_skills = [m.name for m in matched_skills[:4]]
        skills_phrase = ", ".join(top_skills) if top_skills else "modern software engineering"

        if has_jd:
            tailored_summary = (
                f"Results-driven {job_title} with proven expertise in {skills_phrase}. "
                f"Demonstrated track record of delivering resilient, scalable solutions aligned with the technical requirements "
                f"at {company_name}. Adept at designing robust architectures, leading agile execution, and achieving [add verified result, e.g., 30% performance boost]."
            )
            rationale = f"Directly aligns professional headline with target role '{job_title}' and highlights verified competencies matched to {company_name}."
        elif company_name in COMPANY_PROFILES:
            comp_info = COMPANY_PROFILES[company_name]
            tailored_summary = (
                f"Accomplished {job_title} with solid engineering foundation in {skills_phrase}. "
                f"Focused on {comp_info['culture_headline'].lower()}, maintaining high operational standards, "
                f"and delivering measurable business outcomes [add verified result]."
            )
            rationale = f"Weaves in {company_name}'s known engineering tenets ({comp_info['culture_headline']}) while preserving truthful experience."
        else:
            tailored_summary = (
                f"Experienced {job_title} with strong background in {skills_phrase}. "
                f"Dedicated to building dependable, maintainable systems for {company_name}, "
                f"collaborating across cross-functional teams and driving [add verified result]."
            )
            rationale = f"Tailors executive summary specifically for {job_title} position at {company_name}."

        proposed_changes.append(
            ProposedChange(
                id=f"pc-{change_counter}",
                section="summary",
                original_text=structured_resume.summary,
                proposed_text=tailored_summary,
                rationale=rationale,
                evidence_source=guidance_source,
                what_to_verify="Replace '[add verified result]' with a truthful quantifiable accomplishment.",
                is_accepted=True,
            )
        )
        change_counter += 1

    # 2. Experience Bullets Upgrade
    if "experience" in sections_to_improve:
        for exp in structured_resume.experience:
            for b_idx, bullet in enumerate(exp.bullets):
                is_weak, issues, rewrite, what_to_add, verb, _ = analyze_bullet_point(
                    bullet_text=bullet,
                    target_skills=[m.name for m in matched_skills],
                )
                if is_weak:
                    proposed_changes.append(
                        ProposedChange(
                            id=f"pc-{change_counter}",
                            section="experience",
                            target_item_id=exp.id,
                            bullet_index=b_idx,
                            original_text=bullet,
                            proposed_text=rewrite,
                            rationale="; ".join(issues),
                            evidence_source=guidance_source,
                            what_to_verify=what_to_add,
                            is_accepted=True,
                        )
                    )
                    change_counter += 1
                    if change_counter >= 10:
                        break
            if change_counter >= 10:
                break

    # Structure Feedback
    structure_feedback: List[str] = []
    if not structured_resume.summary or len(structured_resume.summary.split()) < 15:
        structure_feedback.append("Professional Summary is short or missing; a 2-3 sentence tailored overview is recommended.")
    if len(structured_resume.experience) == 0:
        structure_feedback.append("Work Experience section should clearly identify employer names, job titles, and dates in reverse chronological order.")
    if not any(structured_resume.skills.values()):
        structure_feedback.append("Skills section should be categorized into clean clusters (Languages, Frameworks, Cloud & Databases) for ATS readability.")

    # Prioritized Improvements Checklist
    prioritized_improvements: List[Dict[str, Any]] = []
    p_counter = 1

    if missing_requirements:
        sample_missing = ", ".join([m.name for m in missing_requirements[:3]])
        prioritized_improvements.append({
            "id": f"imp-{p_counter}",
            "title": f"Review missing qualifications: {sample_missing}",
            "priority": "high",
            "reason": f"These are primary expectations for {job_title} at {company_name}. Confirm if you have genuine experience before including.",
            "requires_confirmation": True,
        })
        p_counter += 1

    if proposed_changes:
        prioritized_improvements.append({
            "id": f"imp-{p_counter}",
            "title": f"Upgrade {len(proposed_changes)} bullet points with verified metrics and active verbs",
            "priority": "high",
            "reason": "Eliminates passive phrasing and introduces clear Action + Task + Method + [Verified Result] structure.",
            "requires_confirmation": False,
        })
        p_counter += 1

    if weakly_evidenced:
        sample_weak = ", ".join([w.name for w in weakly_evidenced[:3]])
        prioritized_improvements.append({
            "id": f"imp-{p_counter}",
            "title": f"Provide project proof for listed skills: {sample_weak}",
            "priority": "medium",
            "reason": "Recruiters and hiring managers look for demonstrated usage in work history, not just keyword mentions.",
            "requires_confirmation": False,
        })
        p_counter += 1

    prioritized_improvements.append({
        "id": f"imp-{p_counter}",
        "title": "Perform single-column ATS typography review",
        "priority": "low",
        "reason": "Ensures resume uses standard headings, zero tables/graphics, and clean bullet formatting.",
        "requires_confirmation": False,
    })

    return TargetedAnalysisResponse(
        target_mode=target_mode.value,
        company_name=company_name,
        industry=industry,
        job_title=job_title,
        has_job_description=has_jd,
        guidance_source=guidance_source,
        summary_overview=(
            f"Tailored analysis for {job_title} at {company_name} ({guidance_source}). "
            f"Identified {len(matched_skills)} matched competencies, {len(missing_requirements)} missing qualifications to review, "
            f"and {len(proposed_changes)} suggested rewrites ready for your approval."
        ),
        matched_skills=matched_skills[:12],
        missing_requirements=missing_requirements[:12],
        weakly_evidenced=weakly_evidenced[:8],
        structure_feedback=structure_feedback,
        prioritized_improvements=prioritized_improvements,
        proposed_changes=proposed_changes,
        draft_resume=structured_resume,
    )


# =============================================================================
# Document Exporters: DOCX and PDF
# =============================================================================

def generate_docx_resume(resume: StructuredResume) -> bytes:
    """
    Generates a clean, ATS-compliant single-column Microsoft Word (.docx) document.
    """
    doc = docx.Document()

    # Set 0.75 inch margins for standard ATS format
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # 1. Contact Header
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = name_p.add_run(resume.contact_info.full_name)
    name_run.font.name = "Calibri"
    name_run.font.size = Pt(20)
    name_run.font.bold = True
    name_run.font.color.rgb = RGBColor(15, 23, 42)

    contact_parts = []
    if resume.contact_info.email:
        contact_parts.append(resume.contact_info.email)
    if resume.contact_info.phone:
        contact_parts.append(resume.contact_info.phone)
    if resume.contact_info.location:
        contact_parts.append(resume.contact_info.location)
    if resume.contact_info.linkedin:
        contact_parts.append(resume.contact_info.linkedin)
    if resume.contact_info.github:
        contact_parts.append(resume.contact_info.github)

    if contact_parts:
        contact_p = doc.add_paragraph()
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_run = contact_p.add_run(" | ".join(contact_parts))
        contact_run.font.name = "Calibri"
        contact_run.font.size = Pt(9.5)
        contact_run.font.color.rgb = RGBColor(71, 85, 105)

    def add_section_heading(title: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title.upper())
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)

    # 2. Professional Summary
    if resume.summary and resume.summary.strip():
        add_section_heading("Professional Summary")
        sp = doc.add_paragraph()
        s_run = sp.add_run(resume.summary.strip())
        s_run.font.name = "Calibri"
        s_run.font.size = Pt(10)
        sp.paragraph_format.space_after = Pt(6)

    # 3. Technical Skills
    has_skills = any(resume.skills.values())
    if has_skills:
        add_section_heading("Technical Skills")
        for cat, items in resume.skills.items():
            if items:
                sk_p = doc.add_paragraph()
                sk_p.paragraph_format.space_after = Pt(2)
                bold_cat = sk_p.add_run(f"{cat}: ")
                bold_cat.font.name = "Calibri"
                bold_cat.font.size = Pt(10)
                bold_cat.font.bold = True
                skills_run = sk_p.add_run(", ".join(items))
                skills_run.font.name = "Calibri"
                skills_run.font.size = Pt(10)

    # 4. Work Experience
    if resume.experience:
        add_section_heading("Professional Experience")
        for exp in resume.experience:
            header_p = doc.add_paragraph()
            header_p.paragraph_format.space_before = Pt(6)
            header_p.paragraph_format.space_after = Pt(2)

            title_run = header_p.add_run(exp.title)
            title_run.font.name = "Calibri"
            title_run.font.size = Pt(10.5)
            title_run.font.bold = True

            comp_run = header_p.add_run(f" | {exp.company}")
            comp_run.font.name = "Calibri"
            comp_run.font.size = Pt(10)
            comp_run.font.italic = True

            dates_str = f" ({exp.start_date or ''} - {exp.end_date or 'Present'})"
            date_run = header_p.add_run(dates_str)
            date_run.font.name = "Calibri"
            date_run.font.size = Pt(9.5)
            date_run.font.color.rgb = RGBColor(100, 116, 139)

            for bullet in exp.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_after = Pt(2)
                b_run = bp.add_run(bullet)
                b_run.font.name = "Calibri"
                b_run.font.size = Pt(9.5)

    # 5. Projects
    if resume.projects:
        add_section_heading("Key Projects")
        for proj in resume.projects:
            pp = doc.add_paragraph()
            pp.paragraph_format.space_before = Pt(4)
            pp.paragraph_format.space_after = Pt(2)
            pt_run = pp.add_run(proj.title)
            pt_run.font.name = "Calibri"
            pt_run.font.size = Pt(10)
            pt_run.font.bold = True

            if proj.technologies:
                tech_run = pp.add_run(f" [{', '.join(proj.technologies)}]")
                tech_run.font.name = "Calibri"
                tech_run.font.size = Pt(9)
                tech_run.font.italic = True

            for bullet in proj.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_after = Pt(2)
                b_run = bp.add_run(bullet)
                b_run.font.name = "Calibri"
                b_run.font.size = Pt(9.5)

    # 6. Education
    if resume.education:
        add_section_heading("Education")
        for edu in resume.education:
            ep = doc.add_paragraph()
            ep.paragraph_format.space_after = Pt(2)
            deg_run = ep.add_run(edu.degree)
            deg_run.font.name = "Calibri"
            deg_run.font.size = Pt(10)
            deg_run.font.bold = True

            inst_run = ep.add_run(f" - {edu.institution}")
            inst_run.font.name = "Calibri"
            inst_run.font.size = Pt(10)

            if edu.graduation_date:
                gr_run = ep.add_run(f" ({edu.graduation_date})")
                gr_run.font.name = "Calibri"
                gr_run.font.size = Pt(9.5)
                gr_run.font.color.rgb = RGBColor(100, 116, 139)

    # 7. Certifications
    if resume.certifications:
        add_section_heading("Certifications")
        for cert in resume.certifications:
            cp = doc.add_paragraph(style="List Bullet")
            cp.paragraph_format.space_after = Pt(2)
            c_run = cp.add_run(cert)
            c_run.font.name = "Calibri"
            c_run.font.size = Pt(9.5)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def generate_pdf_resume(resume: StructuredResume) -> bytes:
    """
    Generates a clean, ATS-compliant single-column PDF document using ReportLab.
    Uses standard vector fonts (Helvetica) with zero image/table trickery.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom Clean Typography
    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,  # Center
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=3,
        textTransform="uppercase",
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        leftIndent=14,
        firstLineIndent=-10,
        textColor=colors.HexColor("#334155"),
        spaceAfter=3,
    )

    story = []

    # 1. Contact Header
    story.append(Paragraph(resume.contact_info.full_name, name_style))

    contact_parts = []
    if resume.contact_info.email:
        contact_parts.append(resume.contact_info.email)
    if resume.contact_info.phone:
        contact_parts.append(resume.contact_info.phone)
    if resume.contact_info.location:
        contact_parts.append(resume.contact_info.location)
    if resume.contact_info.linkedin:
        contact_parts.append(resume.contact_info.linkedin)
    if resume.contact_info.github:
        contact_parts.append(resume.contact_info.github)

    if contact_parts:
        story.append(Paragraph(" &nbsp;|&nbsp; ".join(contact_parts), contact_style))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

    # Helper for Section Title with Divider
    def add_section(title: str):
        story.append(Paragraph(title, heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=5))

    # 2. Professional Summary
    if resume.summary and resume.summary.strip():
        add_section("Professional Summary")
        story.append(Paragraph(resume.summary.strip(), body_style))
        story.append(Spacer(1, 4))

    # 3. Technical Skills
    has_skills = any(resume.skills.values())
    if has_skills:
        add_section("Technical Skills")
        for cat, items in resume.skills.items():
            if items:
                skill_text = f"<b>{cat}:</b> {', '.join(items)}"
                story.append(Paragraph(skill_text, body_style))
        story.append(Spacer(1, 4))

    # 4. Work Experience
    if resume.experience:
        add_section("Professional Experience")
        for exp in resume.experience:
            dates = f" ({exp.start_date or ''} - {exp.end_date or 'Present'})"
            header_text = f"<b>{exp.title}</b> &nbsp;|&nbsp; <i>{exp.company}</i> <font color='#64748b'>{dates}</font>"
            story.append(Paragraph(header_text, body_style))
            for bullet in exp.bullets:
                # Clean characters for ReportLab XML parser
                safe_bullet = bullet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f"&bull; {safe_bullet}", bullet_style))
            story.append(Spacer(1, 4))

    # 5. Projects
    if resume.projects:
        add_section("Key Projects")
        for proj in resume.projects:
            tech = f" [<i>{', '.join(proj.technologies)}</i>]" if proj.technologies else ""
            story.append(Paragraph(f"<b>{proj.title}</b>{tech}", body_style))
            for bullet in proj.bullets:
                safe_bullet = bullet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f"&bull; {safe_bullet}", bullet_style))
            story.append(Spacer(1, 4))

    # 6. Education
    if resume.education:
        add_section("Education")
        for edu in resume.education:
            year = f" ({edu.graduation_date})" if edu.graduation_date else ""
            story.append(Paragraph(f"<b>{edu.degree}</b> - {edu.institution}<font color='#64748b'>{year}</font>", body_style))
        story.append(Spacer(1, 4))

    # 7. Certifications
    if resume.certifications:
        add_section("Certifications")
        for cert in resume.certifications:
            safe_cert = cert.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"&bull; {safe_cert}", bullet_style))

    doc.build(story)
    return buffer.getvalue()
