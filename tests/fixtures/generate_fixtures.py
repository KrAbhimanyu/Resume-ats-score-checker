import os
import io
import docx
from pypdf import PdfWriter


def make_pdf_with_text(text_lines, output_path):
    """Generates a valid standard PDF document with given lines of text."""
    content_stream = "BT\n/F1 10 Tf\n50 750 Td\n15 TL\n"
    for line in text_lines:
        # Escape parenthesis
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_stream += f"({safe_line}) '\n"
    content_stream += "ET"
    stream_bytes = content_stream.encode("latin1", errors="replace")

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    obj4 = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    obj5 = f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") + stream_bytes + b"\nendstream\nendobj\n"

    header = b"%PDF-1.4\n"
    offsets = [0]
    body = b""
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        offsets.append(len(header) + len(body))
        body += obj

    xref_offset = len(header) + len(body)
    xref = f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("latin1")
    trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
    pdf_bytes = header + body + xref + trailer

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)


def make_empty_pdf(output_path):
    """Generates a valid PDF with blank page."""
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    header = b"%PDF-1.4\n"
    offsets = [0]
    body = b""
    for obj in [obj1, obj2, obj3]:
        offsets.append(len(header) + len(body))
        body += obj
    xref_offset = len(header) + len(body)
    xref = f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("latin1")
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("latin1")
    trailer = f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")
    with open(output_path, "wb") as f:
        f.write(header + body + xref + trailer)


def make_docx(paragraphs, output_path):
    """Generates a valid docx file."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(output_path)


def generate_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    resumes_dir = os.path.join(base_dir, "sample_resumes")
    jobs_dir = os.path.join(base_dir, "sample_jobs")
    os.makedirs(resumes_dir, exist_ok=True)
    os.makedirs(jobs_dir, exist_ok=True)

    # 1. Job Descriptions
    fullstack_job = """Senior Full-Stack Software Engineer

About the Role:
We are looking for a Senior Full-Stack Engineer to design, build, and scale resilient cloud applications.

Minimum Qualifications:
- 4+ years of professional software engineering experience
- Bachelor's degree in Computer Science, Software Engineering, or equivalent practical experience
- Strong proficiency in Python, FastAPI, and PostgreSQL
- Extensive experience developing interactive frontends with React and TypeScript
- Hands-on experience with Docker, Kubernetes, and automated CI/CD pipelines
- Proven understanding of REST API design and microservices architecture

Preferred Qualifications:
- Experience with AWS cloud infrastructure (ECS, S3, RDS)
- Familiarity with Redis caching and Kafka message streams
- Strong knowledge of automated unit testing with pytest or Jest
"""
    with open(os.path.join(jobs_dir, "fullstack_engineer.txt"), "w", encoding="utf-8") as f:
        f.write(fullstack_job)

    data_analyst_job = """Data Analyst

Minimum Qualifications:
- 2+ years of experience in data analysis, business intelligence, or reporting
- Bachelor's degree in Mathematics, Statistics, Computer Science, or related field
- Strong SQL querying skills and experience with relational database schemas
- Experience with Python for data manipulation and statistical analysis
- Proven experience building dashboards using Tableau or Power BI
- Advanced Microsoft Excel skills
"""
    with open(os.path.join(jobs_dir, "data_analyst.txt"), "w", encoding="utf-8") as f:
        f.write(data_analyst_job)

    with open(os.path.join(jobs_dir, "empty_job.txt"), "w", encoding="utf-8") as f:
        f.write("")

    # 2. Resumes
    senior_resume_lines = [
        "Alex Morgan - Senior Software Engineer",
        "Email: alex.morgan.fictional@example.com | Location: Remote",
        "Professional Summary",
        "Experienced Full-Stack Engineer with 6+ years of expertise designing and deploying microservices.",
        "Technical Skills",
        "Languages: Python, TypeScript, JavaScript, SQL",
        "Frameworks & Tools: FastAPI, React, PostgreSQL, Docker, Kubernetes, AWS, CI/CD, Git, Redis",
        "Work Experience",
        "Senior Software Engineer - TechCorp (2021 - Present)",
        "- Architected and deployed microservices backend using Python, FastAPI, and PostgreSQL serving 100k daily users.",
        "- Reduced API latency by 35% through Redis caching and query optimization.",
        "- Modernized customer web portal using React and TypeScript, reaching 85% test coverage.",
        "- Automated deployment pipelines using Docker and Kubernetes, reducing release cycle by 50%.",
        "Software Engineer - CloudSystems (2018 - 2021)",
        "- Built REST APIs using Python and PostgreSQL.",
        "- Collaborated with cross-functional teams to deliver 15 features across 4 quarters.",
        "Education",
        "Bachelor of Science in Computer Science - State University (2014 - 2018)",
    ]

    # Save senior resume in both PDF and DOCX
    make_pdf_with_text(senior_resume_lines, os.path.join(resumes_dir, "senior_software_engineer.pdf"))
    make_docx(senior_resume_lines, os.path.join(resumes_dir, "senior_software_engineer.docx"))

    # Entry-level analyst PDF
    analyst_lines = [
        "Jordan Taylor - Junior Data Analyst",
        "Email: jordan.taylor.fictional@example.com",
        "Summary",
        "Junior Data Analyst with 2 years of practical experience extracting data insights.",
        "Skills",
        "SQL, Python, Tableau, Excel, Data Analysis, Git",
        "Work Experience",
        "Junior Data Analyst - RetailMetrics (2022 - Present)",
        "- Wrote complex SQL queries to extract data and created dashboards in Tableau for 25 stakeholders.",
        "- Analyzed customer churn patterns using Python, improving retention by 12%.",
        "Education",
        "Bachelor of Science in Statistics - City College (2018 - 2022)",
    ]
    make_pdf_with_text(analyst_lines, os.path.join(resumes_dir, "entry_level_analyst.pdf"))

    # Minimal resume DOCX
    minimal_lines = [
        "Sam Doe",
        "Looking for general software work. Know basic programming.",
    ]
    make_docx(minimal_lines, os.path.join(resumes_dir, "minimal_resume.docx"))

    # Empty PDF
    make_empty_pdf(os.path.join(resumes_dir, "empty_resume.pdf"))

    # Corrupt PDF
    with open(os.path.join(resumes_dir, "corrupt_file.pdf"), "wb") as f:
        f.write(b"%PDF-1.4\ncorrupted content that cannot be parsed obj<<>>trailer%%EOF")

    print("All fixtures generated successfully!")


if __name__ == "__main__":
    generate_all()
