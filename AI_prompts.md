# AI Prompts

For each Homework 5 problem, this file preserves the prompts I typed in my own words. The prompt text is stored verbatim as provided; only section labels, "What was lacking," and evidence notes are added around it. Each problem section includes its problem number and title.

## Background

These prompts set up the HW5 workspace. They are background rather than problem work.

What was lacking: workspace setup only; no problem instructions yet.

### Prompts

#### Background Prompt 1

we are doing hw5, lets save everything there.

#### Background Prompt 2

i am going to give you a scenario first and then we will get into the problems

#### Background Prompt 3

we need to create a campus customs multi agent operations agentic team that runs the shop. we need open tickets land on a board - customer orders, rent, unpaid bills, discount requests and whatever the shop has to handle. u will build three pieces that talk to each other: an MCP server, a FastAPI Backend with a multiple agent team, and a React dashboard so a himan can watch the agents at work and approve requests. Ther agent team has full connectivity where any agent may delegate tasks to any other agent for help. in the assignment we will build the agents: boss - reads each ticket, deides who should work on it and makes final calls. inventory- checks stock by SKU and size, spots short falls and figures which vendor it needs to restock; accounting - watches cash and invoice check margins and prepares payments or purchas eorders for himan approval; facilities - handles the shop space side (leases, rent, etc.); customer service - drafts messages for customers. do not build anything now but remember this gor when we go on with the problmes

#### Background Prompt 4

in the fokder there is a data.zip so unzip it . so there is data/campus_customs.db. the file is the original shop database. the tables include desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, and invoices. the toos will update the database as tickets get resolved. make a copy of the database file called data/campus_customs_new.db and point ur MCP server and backend at that working copy. keep campus_customs.db untouched so u can reset when u want to restart resolving the tickers. dont do it yet.

#### Background Prompt 5

another thing - rules of this shope. the field desk.date_today is "today" for the shop. use this date to detrmine what is overdue. vendor lead times come from the vendors table;  a vendor cannot ship new product while they still have an open unpaid invoice; human approval is requiref ro any payments; points will be deducted if this is not done. if payment is made, make sure to update the relevant tbale; if there is not enough cash, the pay tool must refuse - we dont want negative balances; cash only goes out in this homework- we are not modelling revenue so no money comes in;before the funn run to resolve the tickets make sure to reset the database to the original values;  do not email customers or call real vendors; drafts tay on the board. for this we want to think of keeping it a bit efficient in terms of tokens but nothing crazy efficient that it cant think properly. so lets just keep that in mind

#### Background Prompt 6

note that similar to last time we will end up having the final submission as a public github repo. so note that

## Problem 1: Vibe Coder Prompts

What was lacking: section title only so far; working prompts to follow.

### Prompts

#### Prompt 1

problem 1: vibe coder prompts

#### Prompt 2

okay that is good. note like usual there will be the problem number and the title. atleast one prompt that i typed, and one follow-up prompt if needed. tell me if it is not completing any of the things written here and let m eknow

## Problem 2: Study the Campus Customs Database

What was lacking: the initial request did not specify where to save the study notes; they were saved to output/database_study.md.

### Prompts

#### Prompt 1

problem 2: study the campus customs database

#### Prompt 2

open data/campus_customs.db and look through every table and its fields. copy the original file to the data/campus_customs_new.db. later on in the pronlems update the working copy. study the three open tickets so you see how they link to other tables.

#### Prompt 3

start the output/harness.md. for each table, list the fields and one short line on why that table matters for the agents. note that we will keep growing this in later problems

## Problem 3: Build the MCP Server

What was lacking: the first prompt did not name the database or say whether to run the server; follow-ups set it to data/campus_customs_new.db and said not to connect or run it yet.

### Prompts

#### Prompt 1

problem 3: build the MCP server.

#### Prompt 2

write the MCP server in mcp_server/ using FastMCP

#### Prompt 3

it will talk to the data/campus_customs_new.db

#### Prompt 4

do not need to connect it or run it in this problem

#### Prompt 5

note that every agent in this homework will use the tools in this MCP server. we will add more tools to it latter on. for now three tools are needed for the tickets in the database. make sure the names are clear. never invent any data. and use only information in the datbaase. in output/harness.md list each of the three mcp tools. for every tool include: which table it reads, which ticket it helps unlock (101,102, 103) and one sentence on why that tool is the right one for that ticket. vague lines like "reads inventro" score low - tie the tool to the ticket. Also make sure to add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has.

## Problem 4: Add the MCP Server to Vibe Coder and Test Each Tool

What was lacking: the prompt did not say which Python to launch the server with; a local .venv with fastmcp was created and .mcp.json points at it.

### Prompts

#### Prompt 1

okay cool. now Problem 4: add the MCP server to vibe coder and test each tool

#### Prompt 2

add the MCP server to this project so you (the vibe coder) can call the tools. save the connection JSOn text in .mcp.json at the project root (or however u save local MCP server lists).

#### Prompt 3

okay one it is connected, test each of the three MCP tools. save the evidence in output/mcp_smoke.json. for every tool include: the prompt asked to the vibe coder (u); the tool name; the tool output (has to match values in data/campus_customs_new.db)

## Problem 5: Build the Agent Team and Grow the MCP Tools

What was lacking: the first build prompt did not say where prompts, types, and agent code should live; the follow-up set backend/prompts/ (one file per agent), backend/models.py, and backend/ for agents. Role boundaries, the audit trail, and token limits also needed explicit follow-ups.

### Prompts

#### Prompt 1

Problem 5: Build the agent team and grow the MCP tools

#### Prompt 2

lets buidl the agentic team for campus customs using pydanticai: boss, inventory, accounting, facilitties, and customer service. include prompts, models, and agent lops so they can delagate work toe ach other with full connectivity

#### Prompt 3

put the agent prompts in backend/prompts/ - one file per agent. put data types in backend/models.py and the agent files under backend/ (your layout can vary as long as the five roles are clear).

#### Prompt 4

so the boss is the one delegating and doing this to all the agents. it is the one that runs the shops. we are trying to pen tickets land on boards so that all the things can be done. remember the scenario i have you before the problems started. remember what each of the five agents do. make sure that the boss does make the final call and is the one that we rely on for the judgement. the inventory agent is only looking at inventory and remember the restock stuff. the accounting one that lokos at cash and invoices and is essnetialyl inchagre of monitoring the margins. so keep that in mind for the facilities, customer service agents as well. and remember we have the tables, etc. so keep that in mind when remembering what each agent needs to do

#### Prompt 5

see if any tools are needed for the agents and add them to the MCP server so they can work on the open tickets. remember the shop dfacts come from the mcp server over data/campus_cusotms_new.db. remember do not invnet a second shop-tools layer that then bypasses MCP. I wanna make sure the agents wires so they append to output/audit_trail.json as they run. for each agent-loop step. make sure to record enough to audit later. append this to the file - do not wipe it each run

#### Prompt 6

in output/harness.md, lit each agent and each MCP tool (including the ones added in this problem). alonfg with whcih tabel the tool sues. also add the short safety section: the guardrails a real businss would want when the agents touch the real customers and real money. make sure that there are also some limits to that the token usage is kept in check.

#### Prompt 7

update mcp_server/README.md so that the tool list matches what u have now

## Problem 6: Plan the Three Tickets

What was lacking: the first brainstorm assumed things the data didn't support (revenue, stock for 101, delivery dates); follow-ups corrected the flows ticket by ticket before desk_tickets.html was built.

### Prompts

#### Prompt 1

Problem 6: Plan the three tickets

#### Prompt 2

before we wirre the backend, lets brainstorm wht we expect each of the team members to do on each open ticket

#### Prompt 3

tell me what each of the tickets are first

#### Prompt 4

okay so for ticket 101 - the boss agent should first take a look at what the customer order is. it then will make the decision which agent will handle this. the decision should be that it should go to inventory to see if there is inventory for what it the customer wants. once that agent lets the boss know that there is inventory, boss will then give it to accounting agent to prepare an invoice so that the revenue, etc. will make sure payment went through and all. it should be see able to see if revenue can be xliamed. then the boss will see ok all this is done, will ask the customer service agent to prepare a message or something that confirms the order to the customer.

#### Prompt 5

in the inventory one why is it looking at the vendor being blocker?

#### Prompt 6

and on the site do we say a gurantee of number of days for delivery?

#### Prompt 7

okay cool then i think that output flow makes sense based on what is aid and the adjusted fir that you made.

#### Prompt 8

now lets go through the 102 ticket my expecation is that again the boss will read the ticket. see that the rent notice is due. and then decide to see who is paying it. look at accounting agent to prepare payment. and faciliites that looks at the leases,rents etc. for 103 my output expectaition is boss read, go to inventory check, go to accounting to prepare something for himan approval. boss interacts with human, and then custoner service

#### Prompt 9

okay now that we documented what i expect lets build output/desk_tickets. html. this is a page that one can double click with one tab per ticket (101,102, 103). also add empty cash and refection tabs for later problems . we can leave them empty gfor now or a note "coming later" for now. on each tab fill an expected section only (leave room for an actual section after u run the agents). for each ticket's expected section write in the words as we document already who the boss will call first and why. all the agent delegations I m expecting not "boss calls everyone". and then add which mcp tools you expect that run to use. remember all the above discussions we just had and use the final ones we decided on for each fo the ticket.

## Problem 7: Backend Routes

What was lacking: the prompt didn't cover how the dashboard sees pending approvals or resumes ticket 103 after a human decision; a GET /api/approvals route and an optional human_note on the run route were added.

### Prompts

#### Prompt 1

Problem 7: Backend routes

#### Prompt 2

now the react frontend dashboard needs a backend it can call. in backend/main.py use FastAPI and add routes so that it can do the following: it should return 3 tickets and whether each is open or resolved; take a ticket ID and run the agent team on that ticket; return recent agent events - see what each agent said and which tools they ised - so the baord can refresh; approve a payment or purchase after the human approves it (then only agents prepare the pay, and the route is what actually changes the cash); retun the current checking balance from cash_accounts; reset the database to the original values when one wants to try and do a fresh run

#### Prompt 3

from the backend/ folder start the server with: uvicorn main:app --reload --port 8000

#### Prompt 4

okay looks good. confirm that the front end dashboard can call the backend

#### Prompt 5

on those routes

#### Prompt 6

okay in output/harness.md list each of the routes in one line (what the url is and what it does)

## Problem 8: Agent Dashboard

What was lacking: the prompt didn't define when a ticket counts as resolved if payments are still pending, or say anything about styling; resolved was set to "run finished and no pending approvals", and follow-ups asked for polished formatting, table-style desks, and images. The first real run blanked the page (a feed auto-scroll effect returned a Promise), which was fixed and guarded with error boundaries.

### Prompts

#### Prompt 1

okay now Problem 8: Agent dashboard

#### Prompt 2

Build the frontend dashboard in frontend/ with React + Vite + TypeScript. remember to call the routes we just built. at the minimum (feel free to expand the capabilitites) should: list all three tickets; let u pick one ticket and start the agent team on it; show each agent what they are saying or doing while the ticket runs; mark the ticket as resolved when it finsihes running; show a short summary of what each agent did on that specific ticket; let a human then approve the pay and.or the purchase when asked; Show the checking balance (it should drop after an approved pay)

#### Prompt 3

make the dashboard look good. in terms of formatting

#### Prompt 4

make the desks look nice. i want them to look like tables, and the tickets are things people can click on

#### Prompt 5

use some sort of images and make it looks nice

#### Prompt 6

i like that

#### Prompt 7

can i open it show me link

#### Prompt 8

when i click run agent for ticket 2. the screen just goes blank fix it

#### Prompt 9

okay nice

#### Prompt 10

done. now make sure the front end talks to the backend at http://localhost:8000. on the back end make sure to let the Vite page origin (usually this should be http://localhost:5173). the browser is essentially allowed to call those routes. Start the board with: npm run dev

#### Prompt 11

The should open the React desk in the browser so we can pick tickets and watch the agents. also make sure to write output/design.md with what we hav chosen together for the dashboard look (i.e., layout how the agents read differently, how the resolved tickets and cash showed up) and why. it should include the creative choices that makes it feel special and something humans would actually enjo using

## Problem 9: Resolve the Tickets

What was lacking: "run until each is solved" needed human approvals the agents can't give, and the dashboard had no clear place to approve a discount; the user approved payments on the board, a Boss-decision card was added for 103, and two bugs (auto-resolving a Boss-blocked ticket, losing run state on restart) were fixed mid-run.

### Prompts

#### Prompt 1

Problem 9: Resolve the tickets

#### Prompt 2

before we test the agents on a run over the 3 tickets, reset the working database data/campus_cutoms_new.db so we start clena. we should note the starting balance ( i think u already have this). then let srun all the hree tickets on the board until each of them is solved. lets then open output/desk_tickets.html from Problem 6. on each of the ticket tab fill the actual section from thsi run: whcih agents worked, what they delegated and which tools they used. keep the expected esection so that we can compare the two

#### Prompt 3

on the cash tab of the same output/desk_tickets.html itemize the money. Starting checking balance (after the reset); for each ticket see how cash changed when the ticket got resolved. and also why that happened (which pay/purchase, dollar amount). Ending checking balance - it must match cash_accounts in the working database. It is possiuble that you have already done this so dont waste tokens if you already meet the criteria. Wrong cash math loses points even if the baord shows every ticket resolved. ALso save: output/resolved_tickets.json - for each ticket make sure to save id, final status, short outcome, what each agent contributed and any human approavals; output/resolved_board.html- a page u can double click w a screenshot of your React board for each resolved ticket. Now append real reuns to output/audit_trail.json. finish the output/harness.md so it covers tables  MCP tools, the 5 agents, API routes, the dashboard , and safety rules

#### Prompt 4

okay i did it and ow see

#### Prompt 5

okay done

#### Prompt 6

okaynow? where do i approve disvount. it doesnt show me. status is blcoked

#### Prompt 7

kay done

#### Prompt 8

yes fix the boss draft issue

#### Prompt 9

okay done make sure to append real runs to output/audit_trail.json and finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard and safety rules

#### Prompt 10

okay maybe we reset db and then go back? kepeing the runs as is

## Problem 10: Reflection

What was lacking: the reflection didn't say where it should go; it was placed in the Reflection tab of output/desk_tickets.html.

### Prompts

#### Prompt 1

Problem 10: Reflection

#### Prompt 2

1. Agent performance

* 101 (tee): strong. Facts right, paid overdue invoice 501 first, draft had no date. The Boss repeated checks before delegating.
* 102 (rent): correct, but the lease was checked three times and an unneeded landlord draft was written.
* 103 (discount): math right (20% off = $928, above cost) and no restock bought with the $160 left. The draft was written before the human decided, one draft leaked internal numbers, and it took 3 runs.

2. Actual vs. Expected

* 101: matched the plan. The $8 restock was never placed.
* 102: matched the plan, apart from the extra lease checks and landlord draft.
* 103: followed the plan’s logic, but drafted too early and took 3 runs instead of 2. Cash ended at $160, as planned.

3. Simpler as one agent

* Ticket 102 is one lookup and one approval, and in 103’s later passes the Boss worked alone and finished. Handoffs added tokens and repeated lookups. The safety rules are in code, not in having more agents.

4. Problems the team could solve

* Mug restock blocked by an overdue vendor invoice.
* October rent notice, where it should flag that $160 can’t cover $2,400.
* A new order for in-stock hoodies with a discount.

5. Problems the team couldn’t solve

* Receiving restocks and shipping orders: needs receive_shipment and fulfill_order tools and a Fulfillment agent.
* Customer payments coming in: needs a record_payment tool, a sales table and a Receivables agent.
* Returns and refunds: needs order lookup, refund approval, a send-approved-message tool and a Returns agent.

OKay this is everything

#### Prompt 3

perfect

## Problem 11: Submit to GitHub

What was lacking: the layout picture had no place for agents.py, prompts/shared.md, or the screenshot folder, so they were merged into main.py, the five role prompts, and resolved_board.html; the repo name/URL still has to be confirmed after publishing.

### Prompts

#### Prompt 1

okay problem 11: Submit to GitHub

#### Prompt 2

We need to push to public github and then i will submit as repo URL to Canvas. also need to put it in output/github_url.txt. Do not push the real .env to GitHub repo. Do include both the database files under data/ (the original and the working  copy). Note the following as the expected file layout: see in picture. Further, README should explain the copy original database to the working copy when u need a clean run, start MCP server, start FastAPI Backend, start the React board, reset the DB before a full three-ticket run.

[Image: expected file layout — hw5/ with AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/ (campus_customs.db, campus_customs_new.db), mcp_server/ (server.py, README.md), frontend/, backend/ (main.py, models.py, prompts/ boss.md, inventory.md, accounting.md, facilities.md, customer_service.md), output/ (harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json, github_url.txt)]
