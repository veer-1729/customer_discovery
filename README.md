# Customer Discovery Lead Research Automation

This project turns a broad company list into a ranked, research-backed customer discovery lead list for our startup.

The system starts with sources like YC company exports, CMU startup pages, accelerator lists, demo day pages, startup databases, or any website containing company names and descriptions. It collects basic company metadata such as name, website, description, category, batch/source, team members, and public links.

It then performs deeper public research on each company using signals like the company website, jobs page, API/docs pages, integrations, status page, changelog, GitHub presence, LinkedIn, Crunchbase, and other public indicators. The goal is to identify companies that likely have the kind of production complexity where our incident RCA product applies: small engineering team, B2B or customer-facing product, backend/platform ownership, on-call or reliability language, API/integration surface, and no obvious mature SRE team.

Instead of only producing a black-box score, the system generates a short research brief explaining what the company does, why it may or may not fit our target customer profile, what public evidence supports that judgment, likely incident or reliability pain points, pros and cons for outreach, and confidence level.

For promising companies, the project also prepares personalized outreach material, including a company-specific summary, likely pain points, a tailored outreach hook, suggested person to contact, and a discovery question.

Overall, this project automates the workflow from broad company discovery to prioritized, evidence-backed, personalized startup outreach.
