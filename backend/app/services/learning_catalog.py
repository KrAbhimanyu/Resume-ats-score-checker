from typing import Any


TRACKS: dict[str, dict[str, Any]] = {
    "python-data-foundations": {
        "id": "python-data-foundations",
        "title": "Python data foundations",
        "category": "technical",
        "level": "Foundational",
        "skills": ["Python", "data structures", "filtering", "aggregation"],
        "summary": "Practice Python functions and data transformations using a bounded, safe evaluator.",
        "lessons": [
            {
                "id": "python-functions",
                "title": "Functions and explicit inputs",
                "minutes": 12,
                "content": (
                    "A function names one operation and makes its inputs and output explicit. Prefer "
                    "small functions that return a value instead of changing unrelated state. Use "
                    "descriptive parameter names, return the same kind of result for similar inputs, "
                    "and handle empty collections intentionally. For example, a score-filtering "
                    "function should receive both the scores and the threshold rather than reading a "
                    "hidden global value."
                ),
                "resource_ids": ["python-tutorial"],
            },
            {
                "id": "python-collections",
                "title": "Collections and transformations",
                "minutes": 14,
                "content": (
                    "Lists preserve order and may contain duplicates; sets represent unique values; "
                    "dictionaries associate keys with values. A list comprehension expresses a "
                    "transformation as [expression for item in items if condition]. Choose a set only "
                    "when uniqueness is part of the requirement. Sorting makes output order explicit "
                    "when a consumer or test needs deterministic results."
                ),
                "resource_ids": ["python-tutorial", "python-data-structures"],
            },
            {
                "id": "python-filter-aggregate",
                "title": "Filter, aggregate, and validate",
                "minutes": 16,
                "content": (
                    "Separate selection from aggregation: first determine which records meet a stated "
                    "condition, then compute a total or count. Test the boundary, an empty input, and "
                    "a value just outside the boundary. This academy's coding evaluator runs a "
                    "restricted expression interpreter against fixed cases; it does not execute "
                    "submitted Python or provide a general-purpose runtime."
                ),
                "resource_ids": ["python-tutorial"],
            },
        ],
        "exercise_ids": ["sum-qualified-scores", "count-completed-records"],
        "assessment": {
            "questions": [
                {
                    "id": "function-contract",
                    "prompt": "What makes a function contract most useful?",
                    "options": [
                        {"id": "a", "label": "It makes inputs, output, and expected behavior clear."},
                        {"id": "b", "label": "It hides dependencies in global variables."},
                        {"id": "c", "label": "It changes unrelated application state."},
                    ],
                    "answer": "a",
                    "explanation": "Clear inputs and outputs make a function easier to use and validate.",
                },
                {
                    "id": "list-set",
                    "prompt": "Which collection is designed to represent unique values?",
                    "options": [
                        {"id": "a", "label": "List"},
                        {"id": "b", "label": "Set"},
                        {"id": "c", "label": "Tuple"},
                    ],
                    "answer": "b",
                    "explanation": "A set represents distinct values; lists preserve duplicates and order.",
                },
                {
                    "id": "comprehension",
                    "prompt": "In a list comprehension, what does the optional if clause do?",
                    "options": [
                        {"id": "a", "label": "Filters which input items are included."},
                        {"id": "b", "label": "Imports another module."},
                        {"id": "c", "label": "Sorts the result automatically."},
                    ],
                    "answer": "a",
                    "explanation": "The if clause includes only input items satisfying its condition.",
                },
                {
                    "id": "edge-cases",
                    "prompt": "Which is a valuable boundary test for a threshold filter?",
                    "options": [
                        {"id": "a", "label": "Only a typical value far above the threshold."},
                        {"id": "b", "label": "A value at the threshold and an empty collection."},
                        {"id": "c", "label": "A second copy of the same typical value."},
                    ],
                    "answer": "b",
                    "explanation": "Boundary and empty-input cases reveal common condition and aggregation errors.",
                },
            ],
        },
        "resources": ["python-tutorial", "python-data-structures"],
        "projects": [
            "Build a small CSV summary that groups records by a field and reports counts. Document input assumptions and test an empty file.",
            "Create a command-line study tracker that stores dated learning sessions and reports totals by topic.",
        ],
        "certifications": ["python-certificate"],
    },
    "communication-foundations": {
        "id": "communication-foundations",
        "title": "Clear communication and active listening",
        "category": "soft_skills",
        "level": "Foundational",
        "skills": ["communication", "active listening", "written communication", "feedback"],
        "summary": "Develop practical communication habits through structured listening, concise writing, and feedback exercises.",
        "lessons": [
            {
                "id": "active-listening",
                "title": "Listen, reflect, clarify",
                "minutes": 10,
                "content": (
                    "Active listening means attending to the speaker, reflecting the central point "
                    "in your own words, and asking a neutral clarifying question before proposing a "
                    "solution. Separate what was observed from your interpretation. In a practice "
                    "conversation, summarize the request, confirm priorities, and agree on the next step."
                ),
                "resource_ids": ["active-listening"],
            },
            {
                "id": "structured-writing",
                "title": "Write for a clear decision",
                "minutes": 12,
                "content": (
                    "For a concise work update, state the purpose first, provide the relevant evidence, "
                    "identify a decision or risk, and name the next action and owner. Use concrete "
                    "language and define acronyms for the audience. Before sending, check whether a "
                    "reader can find the request and deadline quickly."
                ),
                "resource_ids": ["writing-effective-emails"],
            },
            {
                "id": "constructive-feedback",
                "title": "Give specific, actionable feedback",
                "minutes": 12,
                "content": (
                    "Useful feedback describes a specific behavior and its observable effect, then "
                    "offers a practical next step and invites the other person's perspective. Discuss "
                    "the work rather than labeling the person. Ask permission when the topic is "
                    "sensitive, and agree how to follow up."
                ),
                "resource_ids": ["feedback-guide"],
            },
        ],
        "exercise_ids": [],
        "assessment": {
            "questions": [
                {
                    "id": "reflect",
                    "prompt": "A teammate describes a blocker. What is the strongest first response?",
                    "options": [
                        {"id": "a", "label": "Reflect the blocker and ask what outcome they need."},
                        {"id": "b", "label": "Immediately assign blame."},
                        {"id": "c", "label": "Change the subject to your own work."},
                    ],
                    "answer": "a",
                    "explanation": "Reflection and a neutral question confirm understanding before acting.",
                },
                {
                    "id": "update",
                    "prompt": "What helps a reader act on a short project update?",
                    "options": [
                        {"id": "a", "label": "Purpose, evidence, decision or risk, and next action."},
                        {"id": "b", "label": "Unexplained acronyms and background history only."},
                        {"id": "c", "label": "A long list with no owner or request."},
                    ],
                    "answer": "a",
                    "explanation": "A clear purpose and action make the update decision-useful.",
                },
                {
                    "id": "feedback",
                    "prompt": "Which feedback is most actionable?",
                    "options": [
                        {"id": "a", "label": "A personal label with no example."},
                        {"id": "b", "label": "A specific behavior, its effect, and a suggested next step."},
                        {"id": "c", "label": "A vague judgement about attitude."},
                    ],
                    "answer": "b",
                    "explanation": "Behavior and impact provide concrete context for improvement.",
                },
                {
                    "id": "clarify",
                    "prompt": "If a request is ambiguous, what should you do?",
                    "options": [
                        {"id": "a", "label": "Guess without telling the requester."},
                        {"id": "b", "label": "Ask a focused, neutral question about the desired outcome."},
                        {"id": "c", "label": "Ignore it until a deadline passes."},
                    ],
                    "answer": "b",
                    "explanation": "A focused clarification reduces rework and makes assumptions visible.",
                },
            ],
        },
        "resources": ["active-listening", "writing-effective-emails", "feedback-guide"],
        "projects": [
            "Prepare a one-page project brief with audience, objective, evidence, risks, decision requested, and next steps.",
            "Practice a feedback conversation using one observable behavior, its impact, and a mutually agreed follow-up.",
        ],
        "certifications": [],
    },
    "cloud-foundations": {
        "id": "cloud-foundations",
        "title": "Cloud and shared-responsibility foundations",
        "category": "technical",
        "level": "Foundational",
        "skills": ["cloud computing", "Azure", "AWS", "identity and access management"],
        "summary": "Learn core cloud service models, shared responsibility, and identity fundamentals.",
        "lessons": [
            {
                "id": "cloud-service-models",
                "title": "Cloud service models and trade-offs",
                "minutes": 12,
                "content": (
                    "Infrastructure as a Service gives the customer more control over operating "
                    "systems and runtime configuration; Platform as a Service shifts more underlying "
                    "maintenance to the provider; Software as a Service offers a provider-managed "
                    "application. The exact division varies by service. Choose by operational "
                    "responsibility, control, portability, and the requirements of the workload."
                ),
                "resource_ids": ["azure-fundamentals", "cs50-python"],
            },
            {
                "id": "shared-responsibility",
                "title": "Understand shared responsibility",
                "minutes": 14,
                "content": (
                    "Cloud security responsibilities are shared between the service provider and "
                    "customer. The division depends on the service model: the provider secures "
                    "underlying facilities and managed infrastructure, while customers retain "
                    "responsibilities such as identity configuration, data classification, access "
                    "management, and workload settings. Verify each service's responsibility model "
                    "rather than assuming the provider secures customer configuration."
                ),
                "resource_ids": ["azure-fundamentals", "aws-shared-responsibility"],
            },
            {
                "id": "cloud-identity",
                "title": "Apply least privilege to cloud identity",
                "minutes": 14,
                "content": (
                    "Grant an identity only the permissions needed for its task and scope those "
                    "permissions as narrowly as practical. Separate human and workload identities, "
                    "remove unused access, and use stronger authentication for privileged actions. "
                    "Review assignments and audit events. A role name alone does not establish that "
                    "a configuration is secure; validate the actual permissions and scope."
                ),
                "resource_ids": ["azure-identity", "aws-iam"],
            },
        ],
        "exercise_ids": [],
        "assessment": {
            "questions": [
                {
                    "id": "service-model",
                    "prompt": "Which cloud service model generally leaves the customer with the most operating-system control?",
                    "options": [
                        {"id": "a", "label": "Infrastructure as a Service"},
                        {"id": "b", "label": "Software as a Service"},
                        {"id": "c", "label": "A provider-managed end-user application"},
                    ],
                    "answer": "a",
                    "explanation": "IaaS usually leaves customers with more operating-system and runtime responsibility than SaaS.",
                },
                {
                    "id": "shared-duty",
                    "prompt": "Who configures customer identities and access in a cloud account?",
                    "options": [
                        {"id": "a", "label": "The cloud provider always configures every customer identity."},
                        {"id": "b", "label": "The customer retains identity and access configuration responsibilities."},
                        {"id": "c", "label": "No one; cloud services require no access configuration."},
                    ],
                    "answer": "b",
                    "explanation": "Customers retain responsibility for their identity and access configuration.",
                },
                {
                    "id": "least-privilege",
                    "prompt": "What does least privilege mean?",
                    "options": [
                        {"id": "a", "label": "Grant only the access needed for a task, with narrow scope."},
                        {"id": "b", "label": "Give every account administrator access."},
                        {"id": "c", "label": "Share a single privileged account across a team."},
                    ],
                    "answer": "a",
                    "explanation": "Least privilege limits permissions and scope to the task's needs.",
                },
                {
                    "id": "verify-service",
                    "prompt": "Why check a service-specific responsibility model?",
                    "options": [
                        {"id": "a", "label": "Responsibilities can differ by service and service model."},
                        {"id": "b", "label": "All cloud products have identical customer duties."},
                        {"id": "c", "label": "It replaces reviewing actual access settings."},
                    ],
                    "answer": "a",
                    "explanation": "Responsibility boundaries vary, so evaluate the specific service and configuration.",
                },
            ],
        },
        "resources": ["azure-fundamentals", "aws-shared-responsibility", "azure-identity", "aws-iam"],
        "projects": [
            "Draw a cloud architecture for a small web application, mark provider and customer responsibilities, and list least-privilege roles for each actor.",
        ],
        "certifications": ["azure-certification", "aws-certification"],
    },
    "leadership-teamwork": {
        "id": "leadership-teamwork",
        "title": "Teamwork and practical leadership",
        "category": "soft_skills",
        "level": "Developing",
        "skills": ["teamwork", "leadership", "facilitation", "conflict resolution"],
        "summary": "Practice collaborative goal-setting, meeting facilitation, and constructive disagreement.",
        "lessons": [
            {
                "id": "shared-outcomes",
                "title": "Align on shared outcomes",
                "minutes": 10,
                "content": (
                    "A team outcome should describe a result, a measure, a time horizon, and the "
                    "people responsible. Invite affected contributors to identify constraints and "
                    "dependencies. Revisit assumptions when evidence changes instead of treating an "
                    "initial plan as permanent."
                ),
                "resource_ids": ["teamwork-guide"],
            },
            {
                "id": "meeting-facilitation",
                "title": "Facilitate an inclusive meeting",
                "minutes": 12,
                "content": (
                    "Share an agenda and intended decisions in advance. Establish participation "
                    "norms, invite input from people who have not spoken, and distinguish discussion "
                    "from decision-making. End with a recap of decisions, owners, and dates. Share notes "
                    "so people who could not attend can contribute asynchronously."
                ),
                "resource_ids": ["meeting-guide"],
            },
            {
                "id": "constructive-disagreement",
                "title": "Resolve disagreement with evidence",
                "minutes": 12,
                "content": (
                    "State the decision to be made, the criteria, and the evidence each option "
                    "addresses. Ask participants to name uncertainties and consequences. Look for a "
                    "small reversible experiment when it is safe to do so, then agree on who will "
                    "review the result and when."
                ),
                "resource_ids": ["conflict-guide"],
            },
        ],
        "exercise_ids": [],
        "assessment": {
            "questions": [
                {
                    "id": "shared-goal",
                    "prompt": "What is a useful first step when aligning a team?",
                    "options": [
                        {"id": "a", "label": "Agree on the outcome, measure, timeframe, and owners."},
                        {"id": "b", "label": "Assign tasks before understanding the goal."},
                        {"id": "c", "label": "Avoid discussing dependencies."},
                    ],
                    "answer": "a",
                    "explanation": "Shared outcomes and responsibilities make coordination explicit.",
                },
                {
                    "id": "inclusive-meeting",
                    "prompt": "How can a facilitator include people who have not spoken?",
                    "options": [
                        {"id": "a", "label": "Invite input without putting anyone on the spot, and offer async input."},
                        {"id": "b", "label": "Let the most senior person speak for everyone."},
                        {"id": "c", "label": "Remove the agenda."},
                    ],
                    "answer": "a",
                    "explanation": "Multiple participation options support inclusive discussion.",
                },
                {
                    "id": "decision",
                    "prompt": "What should a meeting recap include?",
                    "options": [
                        {"id": "a", "label": "Decisions, owners, and due dates."},
                        {"id": "b", "label": "A transcript without next steps."},
                        {"id": "c", "label": "Only the meeting title."},
                    ],
                    "answer": "a",
                    "explanation": "Decisions, owners, and dates make follow-through clear.",
                },
                {
                    "id": "disagreement",
                    "prompt": "What is a constructive way to address a disagreement?",
                    "options": [
                        {"id": "a", "label": "Compare options against shared criteria and evidence."},
                        {"id": "b", "label": "Treat the loudest opinion as fact."},
                        {"id": "c", "label": "Avoid identifying uncertainty."},
                    ],
                    "answer": "a",
                    "explanation": "Explicit criteria and evidence help teams reason about trade-offs.",
                },
            ],
        },
        "resources": ["teamwork-guide", "meeting-guide", "conflict-guide"],
        "projects": [
            "Facilitate a retrospective with a shared outcome, inclusive participation, documented decisions, owners, and follow-up dates.",
        ],
        "certifications": [],
    },
}


RESOURCES: dict[str, dict[str, str]] = {
    "python-tutorial": {
        "title": "The Python Tutorial",
        "provider": "Python Software Foundation",
        "url": "https://docs.python.org/3/tutorial/",
        "kind": "official documentation",
        "skills": ["Python", "functions", "control flow"],
    },
    "cs50-python": {
        "title": "CS50's Introduction to Programming with Python",
        "provider": "Harvard University",
        "url": "https://cs50.harvard.edu/python/",
        "kind": "course",
        "skills": ["Python", "programming"],
    },
    "python-data-structures": {
        "title": "Data Structures",
        "provider": "Python Software Foundation",
        "url": "https://docs.python.org/3/tutorial/datastructures.html",
        "kind": "official documentation",
        "skills": ["Python", "lists", "sets", "dictionaries"],
    },
    "mdn-learn": {
        "title": "Learn web development",
        "provider": "MDN Web Docs",
        "url": "https://developer.mozilla.org/en-US/docs/Learn_web_development",
        "kind": "official learning documentation",
        "skills": ["HTML", "CSS", "JavaScript"],
    },
    "azure-fundamentals": {
        "title": "Describe cloud concepts",
        "provider": "Microsoft Learn",
        "url": "https://learn.microsoft.com/en-us/training/modules/describe-cloud-compute/",
        "kind": "official learning module",
        "skills": ["cloud computing", "Azure"],
    },
    "aws-shared-responsibility": {
        "title": "Shared Responsibility Model",
        "provider": "Amazon Web Services",
        "url": "https://aws.amazon.com/compliance/shared-responsibility-model/",
        "kind": "official documentation",
        "skills": ["cloud computing", "AWS", "security"],
    },
    "azure-identity": {
        "title": "What is Azure role-based access control (Azure RBAC)?",
        "provider": "Microsoft Learn",
        "url": "https://learn.microsoft.com/en-us/azure/role-based-access-control/overview",
        "kind": "official documentation",
        "skills": ["Azure", "identity and access management"],
    },
    "aws-iam": {
        "title": "Security best practices in IAM",
        "provider": "Amazon Web Services",
        "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
        "kind": "official documentation",
        "skills": ["AWS", "identity and access management"],
    },
    "azure-certification": {
        "title": "Microsoft Certified: Azure Fundamentals",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/",
        "kind": "external certification",
        "skills": ["Azure", "cloud computing"],
    },
    "aws-certification": {
        "title": "AWS Certified Cloud Practitioner",
        "provider": "Amazon Web Services",
        "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/",
        "kind": "external certification",
        "skills": ["AWS", "cloud computing"],
    },
    "python-certificate": {
        "title": "Python Institute certification programs",
        "provider": "Python Institute",
        "url": "https://pythoninstitute.org/certification",
        "kind": "external certification",
        "skills": ["Python"],
    },
    "active-listening": {
        "title": "Active Listening",
        "provider": "SkillsYouNeed",
        "url": "https://www.skillsyouneed.com/ips/active-listening.html",
        "kind": "learning resource",
        "skills": ["active listening", "communication"],
    },
    "writing-effective-emails": {
        "title": "Email and online networking",
        "provider": "Purdue Online Writing Lab",
        "url": "https://owl.purdue.edu/owl/subject_specific_writing/professional_technical_writing/email_etiquette.html",
        "kind": "writing guide",
        "skills": ["written communication"],
    },
    "feedback-guide": {
        "title": "Giving and receiving feedback",
        "provider": "Center for Creative Leadership",
        "url": "https://www.ccl.org/articles/leading-effectively-articles/closing-the-gap-between-intent-and-impact/",
        "kind": "leadership resource",
        "skills": ["feedback", "communication"],
    },
    "teamwork-guide": {
        "title": "Teamwork Skills: Being an Effective Group Member",
        "provider": "University of Minnesota Libraries Publishing",
        "url": "https://open.lib.umn.edu/communication/chapter/9-1-teamwork-skills-being-an-effective-group-member/",
        "kind": "open textbook",
        "skills": ["teamwork", "collaboration"],
    },
    "meeting-guide": {
        "title": "Running Effective Meetings",
        "provider": "Atlassian",
        "url": "https://www.atlassian.com/blog/productivity/how-to-run-effective-meetings",
        "kind": "workplace learning guide",
        "skills": ["facilitation", "leadership"],
    },
    "conflict-guide": {
        "title": "Conflict Resolution",
        "provider": "Harvard Program on Negotiation",
        "url": "https://www.pon.harvard.edu/daily/conflict-resolution/",
        "kind": "professional learning resource",
        "skills": ["conflict resolution", "negotiation"],
    },
}


EXERCISES: dict[str, dict[str, Any]] = {
    "sum-qualified-scores": {
        "id": "sum-qualified-scores",
        "track_id": "python-data-foundations",
        "title": "Sum scores that meet a threshold",
        "prompt": (
            "Define sum_qualified_scores(scores, threshold). Return the sum of scores that are "
            "greater than or equal to threshold. Return 0 when none qualify. Do not mutate the input."
        ),
        "signature": "def sum_qualified_scores(scores, threshold):",
        "cases": [
            {"args": [[4, 7, 9], 7], "expected": 16},
            {"args": [[2, 3], 8], "expected": 0},
            {"args": [[], 5], "expected": 0},
            {"args": [[5, 6], 5], "expected": 11},
        ],
        "allowed_constructs": "A single function with a return expression; list comprehensions; comparisons; sum().",
    },
    "count-completed-records": {
        "id": "count-completed-records",
        "track_id": "python-data-foundations",
        "title": "Count completed learning records",
        "prompt": (
            "Define count_completed(records). Each record is a dictionary with a status key. "
            "Return how many records have status equal to the exact string 'completed'."
        ),
        "signature": "def count_completed(records):",
        "cases": [
            {"args": [[{"status": "completed"}, {"status": "started"}]], "expected": 1},
            {"args": [[],], "expected": 0},
            {"args": [[{"status": "completed"}, {"status": "completed"}]], "expected": 2},
            {"args": [[{"status": "paused"}]], "expected": 0},
        ],
        "allowed_constructs": "A single function with a return expression; list comprehensions; dictionary subscripts; len().",
    },
}


TRACK_ORDER = list(TRACKS)
