# Aerospace Manufacturing Simulator 🚀

**Python | Manufacturing Automation | Cybersecurity | Automated Testing**

## About This Project

I'm building a Python-based simulator that models equipment used in an aerospace manufacturing facility.

The project focuses on manufacturing a fictional product called a **Rocket Turbopump Housing**, a component used in rocket propulsion systems.

My goal is to explore how manufacturing equipment, industrial software, and cybersecurity work together.

The simulator currently models investment casting and heat-treatment equipment. As the project grows, I plan to connect it to industrial monitoring software, production databases, and security tools.

This is a hands-on learning project that brings together my background in precision manufacturing, quality assurance, and cybersecurity.

## What the Simulator Does

The simulator currently models two pieces of manufacturing equipment.

### Investment Casting Equipment (EQ-CAST-001)

Investment casting is a manufacturing process used to create metal parts.

The simulator follows five basic stages:

1. Mold Ready
2. Melt Ready
3. Pouring
4. Solidifying
5. Complete

The equipment model tracks operating states, manufacturing phases, and simulated equipment faults.

### Heat-Treatment Furnace (EQ-HT-001)

Heat treatment uses controlled temperatures to change the properties of metal.

The furnace simulator models three main operations:

- **Heating:** Increases temperature at a configured rate.
- **Holding:** Tracks how long the furnace remains at its target temperature.
- **Cooling:** Decreases temperature at a configured rate.

The simulator also checks for missing information, incorrect settings, and equipment faults.

For now, the temperatures and heating rates are demonstration values rather than actual aerospace manufacturing specifications.

## Equipment Faults and Safety Checks

Manufacturing equipment does not always operate as expected.

To explore these situations, I've added simulated equipment faults and operating safeguards.

The simulator can:

- Activate and identify equipment faults.
- Record fault events with timestamps.
- Prevent certain operations when equipment is not running.
- Reject invalid temperatures, heating rates, and time values.
- Preserve abnormal temperature readings instead of automatically correcting them.

These features help me practice writing software that handles unexpected conditions.

## Automated Testing

The project currently has **61 passing automated tests** using Python's built-in `unittest` framework.

The tests check equipment behavior, manufacturing phases, temperature calculations, fault handling, and invalid inputs.

Automated testing helps me catch mistakes when I add new features or change existing code.

## Tools and Technologies

| Technology | How I'm Using It |
|---|---|
| Python 3.12 | Equipment simulation |
| unittest | Automated software testing |
| Ubuntu 24.04 LTS | Development environment |
| Git | Version control |
| GitHub | Project documentation and code hosting |

### Planned Technologies

| Technology | Planned Purpose |
|---|---|
| OPC UA | Equipment data communication |
| Ignition 8.3 SCADA | Industrial dashboards and monitoring |
| Ignition Tag Historian | Historical process data |
| Manufacturing Database | Production records and quality tracking |
| Wazuh | Cybersecurity monitoring |

These integrations are planned and are not part of the current working simulator.

## Project Files

The project is organized into a few main files:

- `simulator.py`: Starts the simulator and displays equipment information.
- `aero_simulator/equipment.py`: Contains equipment models, operating rules, and simulation functions.
- `test_simulator.py`: Contains automated tests.
- `README.md`: Explains the project.

## How to Run the Simulator

You'll need Python installed on your computer.

**1. Download the project**

`git clone https://github.com/perfectopaque/aerospace-manufacturing-simulator.git`

**2. Open the project folder**

`cd aerospace-manufacturing-simulator`

**3. Create a Python virtual environment**

`python3 -m venv .venv`

**4. Activate the environment on Ubuntu or Linux**

`source .venv/bin/activate`

**5. Run the simulator**

`python simulator.py`

The current program displays basic equipment information. A continuously running manufacturing simulation is still in development.

**6. Run the automated tests**

`python -m unittest -v test_simulator.py`

## Development Progress

### Completed

- [x] Create investment casting and heat-treatment equipment models
- [x] Define manufacturing process phases
- [x] Add equipment fault handling and fault history
- [x] Simulate furnace heating
- [x] Track furnace holding time
- [x] Simulate furnace cooling
- [x] Add automated tests
- [x] Organize Python code into modules
- [x] Publish the project on GitHub

### Coming Next

- [ ] Build complete automated manufacturing cycles
- [ ] Create repeatable equipment fault scenarios
- [ ] Track manufacturing runs, casting lots, and heat-treatment batches
- [ ] Add OPC UA communication
- [ ] Connect equipment data to Ignition SCADA
- [ ] Build industrial monitoring dashboards
- [ ] Store production and quality records
- [ ] Add controlled manufacturing approval steps
- [ ] Integrate Wazuh security monitoring
- [ ] Create end-to-end manufacturing demonstrations

## Why This Project Matters to Me

I have professional experience in precision manufacturing, quality assurance, cybersecurity risk assessment, and AI red-team evaluation.

I've worked with manufacturing equipment, investigated quality problems, and helped improve processes. My cybersecurity background has also taught me the importance of protecting systems and maintaining reliable information.

This project gives me an opportunity to connect those experiences while developing my Python and industrial automation skills.

I'm especially interested in how manufacturing organizations can use technology to improve reliability, traceability, and security.

## Important Note

This is a fictional manufacturing environment created for learning and demonstration purposes.

It does not operate real industrial equipment or represent an approved aerospace manufacturing process.

## Connect With Me

**GitHub:** [perfectopaque](https://github.com/perfectopaque)

**LinkedIn:** [Tracey Chaney](https://www.linkedin.com/in/tracey-chaney)

*Thanks for checking out my project!*
