"""Sample content for the local demo server (no Azure needed)."""
from __future__ import annotations

from .catalog import Target

COMPUTE_SOURCE = "https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/compute-decision-tree"

AZURE_COMPUTE = {
    "title": "Azure compute options",
    "summary": "Azure runs your code on a spectrum of services, from virtual machines you manage yourself "
    "to serverless functions where Azure manages everything but your code.",
    "overview": (
        "Compute is where your application code runs. Azure offers several compute services, and the main "
        "difference between them is **how much you manage versus how much Azure manages**.\n\n"
        "At one end, **Virtual Machines** give you full control of the operating system: you patch it, "
        "secure it and scale it. This is infrastructure as a service (IaaS).\n\n"
        "In the middle, **App Service**, **Azure Kubernetes Service (AKS)** and **Azure Container Apps** run "
        "web apps and containers while Azure looks after much of the platform.\n\n"
        "At the other end, **Azure Functions** runs small pieces of code in response to events, and you pay "
        "mainly for what runs. Choose the most managed option that still meets your requirements."
    ),
    "diagram": {
        "caption": "More control on the left, less to manage on the right",
        "mermaid": (
            "flowchart LR\n"
            '  VM["Virtual Machines<br/>(IaaS)"] --> AKS["Azure Kubernetes Service"]\n'
            '  AKS --> ACA["Container Apps"]\n'
            '  ACA --> APP["App Service"]\n'
            '  APP --> FN["Azure Functions<br/>(serverless)"]'
        ),
    },
    "keyConcepts": [
        {"term": "IaaS", "explanation": "Infrastructure as a service: you rent virtual machines and manage the OS."},
        {"term": "PaaS", "explanation": "Platform as a service: Azure manages the OS and runtime; you deploy code."},
        {"term": "Serverless", "explanation": "Code runs on demand; the platform scales it, including to zero."},
        {"term": "Container", "explanation": "A package of an app and its dependencies that runs the same anywhere."},
        {"term": "Kubernetes", "explanation": "An open-source system that schedules and runs containers at scale."},
        {"term": "Scale out", "explanation": "Adding more instances to handle more load, rather than bigger ones."},
    ],
    "comparison": {
        "caption": "Main Azure compute services",
        "columns": ["Service", "You manage", "Good for"],
        "rows": [
            ["Virtual Machines", "OS, runtime, app", "Lift-and-shift, special OS needs"],
            ["Azure Kubernetes Service", "Cluster config, app", "Many containers, teams using Kubernetes"],
            ["Container Apps", "App and scaling rules", "Containerised APIs and jobs without managing Kubernetes"],
            ["App Service", "App and settings", "Web apps and APIs"],
            ["Azure Functions", "Code only", "Event-driven tasks and short jobs"],
        ],
    },
    "whenToUse": [
        {"option": "Virtual Machines", "useWhen": "You need full control of the OS or software that can't be containerised."},
        {"option": "App Service", "useWhen": "You are hosting a standard web app or API and want little ops work."},
        {"option": "Container Apps", "useWhen": "You have containers and want serverless scaling without running Kubernetes."},
        {"option": "Azure Kubernetes Service", "useWhen": "You run many services and need Kubernetes features and control."},
        {"option": "Azure Functions", "useWhen": "Work is triggered by events such as a queue message, timer or HTTP call."},
    ],
    "pitfalls": [
        "Choosing VMs by habit when a managed service would remove patching work.",
        "Adopting Kubernetes for one or two small apps that App Service or Container Apps would run more simply.",
        "Ignoring cold starts when using serverless plans for latency-sensitive APIs.",
        "Not setting autoscale rules, so apps are either over-provisioned or overloaded.",
    ],
    "quiz": [
        {
            "question": "Which option gives you the most control over the operating system?",
            "options": ["Azure Functions", "App Service", "Virtual Machines", "Container Apps"],
            "answerIndex": 2,
            "explanation": "Virtual Machines are IaaS: you manage the operating system yourself.",
        },
        {
            "question": "You need to run code each time a message lands on a queue. What fits best?",
            "options": ["Azure Functions", "Virtual Machines", "Azure Kubernetes Service", "A dedicated VM scale set"],
            "answerIndex": 0,
            "explanation": "Functions are built for event-driven work such as queue triggers.",
        },
        {
            "question": "What does 'serverless' mean for you as the developer?",
            "options": [
                "There are no servers anywhere",
                "You manage the servers but not the network",
                "The platform provisions and scales servers; you supply code",
                "Your app must run in a browser",
            ],
            "answerIndex": 2,
            "explanation": "Servers still exist, but the platform handles them and scaling.",
        },
    ],
    "sources": [{"title": "Choose an Azure compute service", "url": COMPUTE_SOURCE}],
}


def demo_page(target: Target) -> dict:
    """A clearly labelled placeholder page for the demo drafting flow."""
    if target.page_id == "azure--compute":
        return AZURE_COMPUTE
    name = f"{target.subtopic_name}: {target.area_name}"
    return {
        "title": f"{name} (demo draft)",
        "summary": "Demo content created by the local server. In Azure this page is drafted by Azure OpenAI "
        "from Microsoft Learn.",
        "overview": f"This is a **demo draft** for *{name}*.\n\nIn a deployed environment the content job "
        f"searches Microsoft Learn for “{target.query}”, fetches the top pages, and asks Azure OpenAI to "
        "write this page in the KnowNow format.",
        "diagram": {
            "caption": "How a page is produced",
            "mermaid": 'flowchart LR\n  A["Microsoft Learn"] --> B["Azure OpenAI draft"] --> C["Automated checks"] '
            '--> D["Reviewer"] --> E["Published"]',
        },
        "keyConcepts": [
            {"term": "Draft", "explanation": "A generated page waiting for review."},
            {"term": "Checks", "explanation": "Automatic tests of format, quiz and sources."},
            {"term": "Reviewer", "explanation": "A named expert who approves or rejects drafts."},
            {"term": "Published", "explanation": "A page readers can see."},
        ],
        "comparison": {
            "caption": "Page states",
            "columns": ["State", "Visible to readers"],
            "rows": [["Draft", "No"], ["Rejected", "No"], ["Published", "Yes"]],
        },
        "whenToUse": [
            {"option": "Approve", "useWhen": "The page is accurate and clear."},
            {"option": "Reject", "useWhen": "Something is wrong; say what in the reason."},
        ],
        "pitfalls": ["Approving without reading the sources", "Leaving the reason empty", "Ignoring failed checks"],
        "quiz": [
            {
                "question": "Who can see a draft?",
                "options": ["Everyone", "Reviewers only", "Nobody", "Only its author"],
                "answerIndex": 1,
                "explanation": "Drafts appear only in the Review area.",
            },
            {
                "question": "Where does page content come from in Azure?",
                "options": ["Random websites", "Microsoft Learn", "The reviewer types it", "A spreadsheet"],
                "answerIndex": 1,
                "explanation": "The job uses Microsoft Learn pages as its sources.",
            },
            {
                "question": "What happens when you approve a draft?",
                "options": ["It is deleted", "It is published", "It is redrafted", "Nothing"],
                "answerIndex": 1,
                "explanation": "Approving publishes the page for readers.",
            },
        ],
        "sources": [{"title": "Choose an Azure compute service", "url": COMPUTE_SOURCE}],
    }
