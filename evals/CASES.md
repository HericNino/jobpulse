# Evaluation cases

30 hand-written postings with expected answers. The companies are made up. The labels were written
by hand together with the cases, so check them before trusting a score: a wrong label caps the score
for reasons that have nothing to do with the analyzer.

Skills marked *also acceptable* don't count against precision when predicted, and aren't needed for recall.
Skills outside the vocabulary in `src/jobpulse/skills.py` are not scored.

| id | tags | required skills | seniority | work mode | salary |
|---|---|---|---|---|---|
| de-python-senior | backend, de | AWS, Django, Docker, PostgreSQL, Python | senior | hybrid | 65000–80000 EUR/year |
| en-frontend-junior | frontend, en | CSS, React, Testing, TypeScript | junior | remote | 38000–45000 EUR/year |
| en-java-backend | backend, en, trap | Java, Kafka, Microservices, REST APIs, Spring | mid | onsite | none |
| en-react-native | mobile, en, trap | Android, React Native, TypeScript, iOS | mid | remote | 110000–135000 USD/year |
| en-sales-ops | non-tech, en | SQL | unknown | onsite | none |
| en-data-contractor | data, en | Airflow, Python, SQL, Snowflake, dbt | senior | remote | 70–85 EUR/hour |
| en-platform-senior | devops, en | AWS, CI/CD, Kubernetes, Linux, Terraform | senior | hybrid | 80000–95000 EUR/year |
| fr-dotnet | backend, fr | .NET, Azure, C#, SQL | mid | hybrid | 45000–55000 EUR/year |
| en-ml-engineer | ai, en | AWS, Docker, LLMs, Machine Learning, PyTorch, Python | mid | remote | 160000–200000 USD/year |
| en-eng-lead | backend, en | Go, Kafka, Kubernetes, PostgreSQL | lead | hybrid | none |
| hr-intern | intern, hr | Git | intern | onsite | 1000–1000 EUR/month |
| hr-fullstack | fullstack, hr | Docker, MongoDB, Node.js, React, TypeScript | mid | hybrid | 2200–2800 EUR/month |
| en-customer-success | non-tech, en | – | unknown | remote | none |
| en-data-analyst | data, en | Power BI, SQL | junior | onsite | 35000–40000 GBP/year |
| en-staff-rust | systems, en | C++, Linux, Rust | lead | remote | 210000–250000 USD/year |
| en-sre-word-traps | devops, en, trap | GCP, Kubernetes, Python, Terraform | unknown | remote | none |
| de-data-scientist | data, de | Machine Learning, Pandas, Python, SQL, Tableau | junior | onsite | 52000–52000 EUR/year |
| en-vue-senior | frontend, en | GraphQL, TypeScript, Vue | senior | remote | 90000–110000 EUR/year |
| en-cloud-consultant | devops, en | Terraform | mid | hybrid | none |
| en-php-contract | backend, en | Laravel, MySQL, PHP | unknown | remote | 4000–5000 USD/month |
| en-android-pln | mobile, en | Android, CI/CD, Kotlin | senior | onsite | 22000–28000 PLN/month |
| en-ai-engineer | ai, en | FastAPI, LLMs, PostgreSQL, Python | mid | remote | none |
| en-qa-automation | qa, en | CI/CD, Testing, TypeScript | unknown | hybrid | 50000–50000 EUR/year |
| en-dotnet-angular | fullstack, en | .NET, Angular, C#, SQL | senior | onsite | none |
| en-devops-junior-no-salary | devops, en, trap | AWS, Docker, Linux | junior | remote | none |
| en-founding-equity | fullstack, en, trap | Next.js, PostgreSQL, TypeScript | senior | onsite | none |
| de-werkstudent | intern, de | Git, Java, Spring | intern | hybrid | 15–15 EUR/hour |
| en-python-mid | backend, en | AWS, Flask, Python, Redis | mid | remote | none |
| en-head-of-data | data, en | Airflow, SQL, Snowflake, dbt | lead | hybrid | 95000–115000 GBP/year |
| en-elixir | backend, en | Docker, PostgreSQL | unknown | remote | none |

## de-python-senior

**Senior Python Entwickler (m/w/d)**, Kranich Logistik GmbH, Berlin

````text
Wir suchen eine:n Senior Python Entwickler:in für unser Routing-Team. Du baust Services mit Python und Django, unsere Daten liegen in PostgreSQL, deployt wird mit Docker auf AWS. Du bringst mindestens 5 Jahre Berufserfahrung mit. Hybrides Arbeiten: 2 Tage pro Woche im Büro in Berlin. Gehalt: 65.000 – 80.000 € brutto im Jahr.
````

- Required skills: AWS, Django, Docker, PostgreSQL, Python
- Seniority: senior; work mode: hybrid
- Salary: 65000–80000 EUR per year

## en-frontend-junior

**Junior Frontend Developer**, Petalcraft, Remote (EU)

````text
Join our small product team as a junior frontend developer (0-2 years of experience). You'll build UI in React and TypeScript, style it with Tailwind, and write unit tests with Jest. Fully remote within the EU. Salary €38k–45k.
````

- Required skills: CSS, React, Testing, TypeScript
- Also acceptable: JavaScript
- Seniority: junior; work mode: remote
- Salary: 38000–45000 EUR per year

## en-java-backend

**Backend Engineer (Java)**, Northgate Insurance, Munich

````text
This is a pure backend role. You'll write Java with Spring Boot, build event-driven microservices on Kafka, and own REST APIs used by our web app (the frontend team works in JavaScript, but you won't). 3+ years of professional Java experience. Office-based in Munich, five days a week.
````

- Required skills: Java, Kafka, Microservices, REST APIs, Spring
- Also acceptable: JavaScript
- Seniority: mid; work mode: onsite
- Salary: none stated
- Note: JavaScript is mentioned but not required; Java must not be confused with it

## en-react-native

**Mobile Engineer**, Ferngrove Health, Remote (US)

````text
Build our patient app in React Native with TypeScript. You have shipped apps to both the App Store (iOS) and Google Play (Android) and have at least 3 years of mobile experience. Remote. Pay: $110,000 - $135,000 per year.
````

- Required skills: Android, React Native, TypeScript, iOS
- Seniority: mid; work mode: remote
- Salary: 110000–135000 USD per year
- Note: React Native must not be counted as React

## en-sales-ops

**Sales Operations Analyst**, Brightlane, London

````text
Support our sales team with pipeline reporting. You'll keep Salesforce tidy, build forecasts in Excel and pull the occasional report with basic SQL. Office-based in London.
````

- Required skills: SQL
- Seniority: unknown; work mode: onsite
- Salary: none stated
- Note: non-tech role; only SQL is a real skill

## en-data-contractor

**Senior Data Engineer (Contract)**, Morrow Analytics, Remote

````text
6-month contract, fully remote. You'll design pipelines in Airflow, model data with dbt on Snowflake and write a lot of SQL and Python. 6+ years in data engineering. Rate: €70–85/hour.
````

- Required skills: Airflow, Python, SQL, Snowflake, dbt
- Seniority: senior; work mode: remote
- Salary: 70–85 EUR per hour

## en-platform-senior

**Senior Platform Engineer**, Quayside, Amsterdam (hybrid)

````text
Run our Kubernetes platform on AWS. Everything is in Terraform and shipped through GitHub Actions. You're comfortable on Linux and with Prometheus. Experience with Go is a plus. Hybrid, two office days in Amsterdam. €80,000 to €95,000.
````

- Required skills: AWS, CI/CD, Kubernetes, Linux, Terraform
- Also acceptable: Go
- Seniority: senior; work mode: hybrid
- Salary: 80000–95000 EUR per year
- Note: Go is nice-to-have, so it is allowed but not required

## fr-dotnet

**Développeur .NET confirmé (H/F)**, Atelier Numérique, Paris

````text
Nous recherchons un développeur C# / .NET avec 4 ans d'expérience. Vous travaillerez sur Azure et SQL Server. Télétravail 2 jours par semaine. Salaire : 45-55 K€ brut annuel.
````

- Required skills: .NET, Azure, C#, SQL
- Seniority: mid; work mode: hybrid
- Salary: 45000–55000 EUR per year

## en-ml-engineer

**Machine Learning Engineer**, Lattice Bio, Remote (US only)

````text
Train and fine-tune models with PyTorch and ship them as Python services in Docker on AWS (SageMaker). You'll also work on LLM-based features. 4+ years of experience. Salary $160k–$200k plus equity.
````

- Required skills: AWS, Docker, LLMs, Machine Learning, PyTorch, Python
- Seniority: mid; work mode: remote
- Salary: 160000–200000 USD per year

## en-eng-lead

**Engineering Lead, Payments**, Coinbridge, Dublin

````text
Lead a team of six engineers building payment services in Go on PostgreSQL and Kafka, deployed to Kubernetes. Hybrid, three days a week in our Dublin office.
````

- Required skills: Go, Kafka, Kubernetes, PostgreSQL
- Seniority: lead; work mode: hybrid
- Salary: none stated

## hr-intern

**Praksa: Software Engineering (ljeto 2027)**, Brodogradnja Digital, Zagreb

````text
Tražimo studente za ljetnu praksu. Programiraš u Pythonu ili Javi i koristiš Git. Rad u uredu u Zagrebu. Naknada: 1.000 EUR neto mjesečno.
````

- Required skills: Git
- Also acceptable: Java, Python
- Seniority: intern; work mode: onsite
- Salary: 1000–1000 EUR per month
- Note: Python OR Java: either is fine, neither strictly required

## hr-fullstack

**Full-stack developer (m/ž)**, Adriatik Soft, Zagreb

````text
Razvijaš web aplikacije u Node.js-u i Reactu s TypeScriptom, podaci su u MongoDB-u, a sve pakiramo u Docker. Tražimo najmanje 3 godine iskustva. Rad od kuće 2 dana tjedno. Plaća 2.200 – 2.800 EUR neto mjesečno.
````

- Required skills: Docker, MongoDB, Node.js, React, TypeScript
- Seniority: mid; work mode: hybrid
- Salary: 2200–2800 EUR per month

## en-customer-success

**Customer Success Manager**, Tandem HR, Remote

````text
Own relationships with 40 mid-market customers. You love learning new tools and keep everything organised in our CRM. Remote-first team.
````

- Required skills: none
- Seniority: unknown; work mode: remote
- Salary: none stated
- Note: no technical skills at all

## en-data-analyst

**Junior Data Analyst**, Hollins & Rae, Manchester

````text
1-2 years of experience with SQL and Power BI. Python is nice to have. You'll work from our Manchester office. Salary £35,000 - £40,000.
````

- Required skills: Power BI, SQL
- Also acceptable: Python
- Seniority: junior; work mode: onsite
- Salary: 35000–40000 GBP per year

## en-staff-rust

**Staff Software Engineer**, Ironbark Storage, Remote

````text
Design our distributed storage engine in Rust and C++ on Linux. Remote. Compensation $210k-$250k.
````

- Required skills: C++, Linux, Rust
- Seniority: lead; work mode: remote
- Salary: 210000–250000 USD per year

## en-sre-word-traps

**Site Reliability Engineer**, Kestrel Media, Remote

````text
You'll go on-call one week a month and help with the spring cleaning of our alerting. Day to day: Python tooling, Terraform, Kubernetes on GCP. Remote.
````

- Required skills: GCP, Kubernetes, Python, Terraform
- Seniority: unknown; work mode: remote
- Salary: none stated
- Note: 'go' and 'spring' are ordinary words here, not Go or Spring

## de-data-scientist

**Data Scientist (w/m/d)**, Hanse Retail AG, Hamburg

````text
Du analysierst Kundendaten mit Python und Pandas, baust Machine-Learning-Modelle und erstellst Dashboards in Tableau. SQL setzen wir voraus. Berufseinsteiger:innen willkommen. Arbeit vor Ort in Hamburg. Gehalt: 52.000 € p.a.
````

- Required skills: Machine Learning, Pandas, Python, SQL, Tableau
- Seniority: junior; work mode: onsite
- Salary: 52000–52000 EUR per year

## en-vue-senior

**Senior Frontend Engineer**, Wavelength, Remote (EU)

````text
Senior role on our Vue 3 / Nuxt app written in TypeScript, talking to a GraphQL API. Remote within the EU. Salary 90-110k EUR.
````

- Required skills: GraphQL, TypeScript, Vue
- Seniority: senior; work mode: remote
- Salary: 90000–110000 EUR per year

## en-cloud-consultant

**Cloud Consultant**, Meridian Partners, Vienna

````text
Help clients move to the cloud. You know at least one of AWS, Azure or GCP well; Terraform is a must. 3-5 years of consulting or ops experience. Hybrid.
````

- Required skills: Terraform
- Also acceptable: AWS, Azure, GCP
- Seniority: mid; work mode: hybrid
- Salary: none stated
- Note: any one cloud is enough, so none of the three is strictly required

## en-php-contract

**Backend Developer (contract)**, Pinecrest Studio, Remote

````text
Maintain our Laravel (PHP) API and MySQL database. Remote contract. $4,000–$5,000/month.
````

- Required skills: Laravel, MySQL, PHP
- Seniority: unknown; work mode: remote
- Salary: 4000–5000 USD per month

## en-android-pln

**Sr. Android Developer**, Wisła Apps, Warsaw

````text
Build Android apps in Kotlin. You'll own our CI/CD pipelines too. Office in Warsaw. PLN 22,000–28,000 per month (B2B).
````

- Required skills: Android, CI/CD, Kotlin
- Seniority: senior; work mode: onsite
- Salary: 22000–28000 PLN per month

## en-ai-engineer

**AI Engineer (LLM applications)**, Quillmate, Remote

````text
Build LLM features with retrieval (RAG) in Python and FastAPI, with PostgreSQL and pgvector for storage. 2+ years building production software. Remote.
````

- Required skills: FastAPI, LLMs, PostgreSQL, Python
- Seniority: mid; work mode: remote
- Salary: none stated

## en-qa-automation

**QA Automation Engineer**, Fairway Travel, Lisbon (hybrid)

````text
Write end-to-end tests in Playwright and Cypress with TypeScript and run them in our CI/CD. Hybrid. €50k.
````

- Required skills: CI/CD, Testing, TypeScript
- Seniority: unknown; work mode: hybrid
- Salary: 50000–50000 EUR per year

## en-dotnet-angular

**.NET Developer**, Granite Finance, Frankfurt

````text
7 years of experience with C# and .NET, Angular on the frontend, SQL Server. Our pipelines run in Azure DevOps. On-site in Frankfurt.
````

- Required skills: .NET, Angular, C#, SQL
- Also acceptable: Azure, CI/CD
- Seniority: senior; work mode: onsite
- Salary: none stated

## en-devops-junior-no-salary

**Junior DevOps Engineer**, Orbit Labs, Remote

````text
Junior role: Docker, Linux, Bash scripting and AWS basics. Remote. We offer a competitive salary and learning budget.
````

- Required skills: AWS, Docker, Linux
- Seniority: junior; work mode: remote
- Salary: none stated
- Note: 'competitive salary' gives no amount, so salary must stay empty

## en-founding-equity

**Founding Engineer**, Tidewell, San Francisco

````text
Be our first engineer. TypeScript, Next.js and PostgreSQL. 5+ years of experience. In-person in SF. Equity: 0.5–1%.
````

- Required skills: Next.js, PostgreSQL, TypeScript
- Seniority: senior; work mode: onsite
- Salary: none stated
- Note: equity is not a salary

## de-werkstudent

**Werkstudent Softwareentwicklung (m/w/d)**, Rheintal IT, Köln

````text
Neben dem Studium entwickelst du mit Java und Spring Boot, Versionierung mit Git. Hybrid möglich. 15 € pro Stunde.
````

- Required skills: Git, Java, Spring
- Seniority: intern; work mode: hybrid
- Salary: 15–15 EUR per hour

## en-python-mid

**Mid-level Python Developer**, Sable Robotics, Remote

````text
Flask services backed by Redis, background jobs with Celery, deployed on AWS. Remote.
````

- Required skills: AWS, Flask, Python, Redis
- Seniority: mid; work mode: remote
- Salary: none stated

## en-head-of-data

**Head of Data**, Cobalt Energy, London (hybrid)

````text
Lead the data team. Our stack is dbt on Snowflake with Airflow, plus a lot of SQL and Looker. Hybrid. £95k–£115k.
````

- Required skills: Airflow, SQL, Snowflake, dbt
- Seniority: lead; work mode: hybrid
- Salary: 95000–115000 GBP per year

## en-elixir

**Backend Engineer**, Nimbus Chat, Remote

````text
Our backend is Elixir and Phoenix on PostgreSQL, shipped in Docker. Remote.
````

- Required skills: Docker, PostgreSQL
- Seniority: unknown; work mode: remote
- Salary: none stated
- Note: Elixir and Phoenix are outside the skill vocabulary and are not scored
