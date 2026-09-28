\# Agentic Job Hunter



An autonomous AI-powered job search and recommendation system.



Agentic Job Hunter uses LLM agents, browser automation, workflow orchestration, and persistent memory to discover suitable jobs from a candidate resume, evaluate job fit, and provide ranked recommendations.



\---



\# Overview



Traditional job search requires manually searching job boards, reading job descriptions, and comparing requirements with personal experience.



This project builds an autonomous workflow:



```

Resume

&#x20; |

&#x20; v

Resume Understanding Agent

&#x20; |

&#x20; v

Role Discovery Agent

&#x20; |

&#x20; v

Browser Job Search Agent

&#x20; |

&#x20; v

Job Matching Agent

&#x20; |

&#x20; v

Ranking Agent

&#x20; |

&#x20; v

Human Review

&#x20; |

&#x20; v

SQLite Memory

```



The system can:



\- Understand candidate background from a resume

\- Discover realistic career directions

\- Search real job listings through browser automation

\- Extract structured job information

\- Compare resume skills against job requirements

\- Rank opportunities by compatibility

\- Keep application workflow state



\---



\# Features



\## 1. Resume Understanding



Pipeline:



```

resume.pdf

&#x20;   |

&#x20;   v

PDF Parser

&#x20;   |

&#x20;   v

resume.txt

&#x20;   |

&#x20;   v

LLM Structuring

&#x20;   |

&#x20;   v

resume.json

```



Extracts:



\- Education

\- Skills

\- Projects

\- Research experience

\- Work experience



\---



\## 2. Role Discovery Agent



Instead of forcing predefined job searches, the system analyzes the resume and generates realistic target roles.



Example:



Input:



```

Candidate background:

Pharmaceutical chemistry undergraduate

```



Output:



```

Recommended Roles:



\- Pharmaceutical QC Analyst

\- Natural Product Research Assistant

\- Drug Synthesis Assistant

\- Laboratory Technician

```



\---



\## 3. Autonomous Job Search Agent



Uses Browser Use + DeepSeek to search real job pages.



Capabilities:



\- Browser automation

\- Multi-step navigation

\- Job page extraction

\- Structured output generation



Extracts:



\- Job title

\- Company

\- Location

\- Skills

\- Experience requirements

\- URL



\---



\## 4. Resume-Job Matching Agent



The matching system evaluates:



```

Candidate Resume

&#x20;       +

Job Description

&#x20;       |

&#x20;       v

Match Analysis

```



Produces:



\- Match score

\- Matched skills

\- Missing skills

\- Transferable strengths

\- Improvement suggestions



\---



\## 5. Ranking System



Instead of blindly returning search results:



```

10 Candidate Jobs



&#x20;       |

&#x20;       v



Matching Agent



&#x20;       |

&#x20;       v



Ranking



&#x20;       |

&#x20;       v



Top Recommendations

```



Low-quality matches are filtered.



\---



\## 6. Human-in-the-loop Approval



The system does not automatically apply for jobs.



Before further actions:



```

Agent Recommendation



&#x20;       |

&#x20;       v



Human Review



&#x20;       |

&#x20;       +---- Approve

&#x20;       |

&#x20;       +---- Skip

&#x20;       |

&#x20;       +---- Reject

```



Human decisions are stored.



\---



\## 7. MCP Tool Server



The project exposes MCP tools:



Available tools:



```

get\_candidate\_profile()



get\_target\_roles()



get\_recommended\_jobs()



list\_jobs()



get\_job\_details()



update\_application\_status()

```



Agents can access candidate data and job state through standardized tools.



\---



\# Architecture



```

&#x20;                   Resume PDF

&#x20;                       |

&#x20;                       v

&#x20;             Resume Parser Agent

&#x20;                       |

&#x20;                       v

&#x20;                 resume.json

&#x20;                       |

&#x20;                       v

&#x20;            Role Discovery Agent

&#x20;                       |

&#x20;                       v

&#x20;             target\_roles.json

&#x20;                       |

&#x20;                       v

&#x20;           Browser Job Search Agent

&#x20;                       |

&#x20;                       v

&#x20;                  jobs.json

&#x20;                       |

&#x20;                       v

&#x20;            Job Matching Agent

&#x20;                       |

&#x20;                       v

&#x20;                matches.json

&#x20;                       |

&#x20;                       v

&#x20;             Ranking / Filtering

&#x20;                       |

&#x20;                       v

&#x20;               Human Review

&#x20;                       |

&#x20;                       v

&#x20;             SQLite Persistent Memory

```



\---



\# Tech Stack



\## LLM



\- DeepSeek API



\## Agent Framework



\- Browser Use

\- LangGraph

\- Model Context Protocol (MCP)



\## Backend



\- Python

\- Pydantic

\- SQLite



\## Automation



\- Browser automation

\- Structured extraction

\- Workflow orchestration



\---



\# Project Structure



```

agentic-job-hunter/



├── agent.py

├── role\_discovery.py

├── match\_agent.py

├── rank\_jobs.py

├── workflow.py

├── workflow\_hitl.py

├── mcp\_server.py

├── database.py



├── data/



│   ├── resume.pdf

│   ├── resume.json

│   ├── target\_roles.json

│   ├── matches.json

│   ├── top\_jobs.json

│   └── agentic\_job\_hunter.db



├── pyproject.toml

└── README.md

```



\---



\# Installation



\## Requirements



\- Python 3.12

\- uv



Install dependencies:



```bash

uv sync

```



Create `.env`:



```

DEEPSEEK\_API\_KEY=your\_api\_key

```



\---



\# Run Complete Workflow



Run:



```bash

uv run workflow.py

```



Workflow:



```

Resume Analysis



↓



Role Discovery



↓



Job Search



↓



Job Matching



↓



Ranking

```



\---



\# Example Output



Example:



```

TOP RECOMMENDED JOBS



\#1

Research Assistant @ Company A



Match Score:

82/100



Missing Skills:

\- Python

\- Data Analysis



Recommendation:

Build data analysis skills and apply.

```



\---



\# Engineering Highlights



This project demonstrates:



\- Multi-agent architecture

\- Autonomous browser interaction

\- Structured LLM output

\- Resume understanding

\- Job recommendation workflow

\- Persistent state management

\- Human-in-the-loop control

\- MCP tool integration

\- Workflow orchestration with LangGraph



\---



\# Future Improvements



Possible extensions:



\- Agent tracing and observability

\- Vector database memory

\- Web dashboard

\- Docker deployment

\- More advanced evaluation framework

\- Personalized application assistant



