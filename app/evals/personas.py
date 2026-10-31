# -*- coding: utf-8 -*-
"""
Synthetic Personas for Sewa Setu Old Age Pension Scheme Evaluations.
Realistic citizen profiles reflecting Purvanchal's elderly population, demographics,
dialects, and administrative edge cases.
"""

PERSONAS = [
    {
        "id": "persona_1_phuleswari",
        "name": "Phuleswari Saikia",
        "age": 71,
        "dob": "12/03/1955",
        "gender": "Female",
        "marital_status": "Widowed",
        "husband_name": "Late Bhaben Saikia",
        "village": "Derial",
        "block": "Sonari",
        "mobile": "9854011221",
        "bank_account": "98765432101",
        "ifsc": "SBIN0001234",
        "role": "citizen",
        "language_style": "Assamese-inflected English; polite, elderly rural grandmother assisted by granddaughter Gita.",
        "dialogue_prompt": (
            "Pranam babu, I am Phuleswari Saikia from Derial village, Sonari. My granddaughter Gita is typing on her phone. "
            "I was born on 12/03/1955 so I am 71 years old. My husband Bhaben passed away three years ago. "
            "I have an SBI bank account in Sonari branch: 98765432101, IFSC SBIN0001234. "
            "Please help me apply for the 250 rupees old age pension."
        ),
        "intent": "fresh_application",
        "expected_result": "SUCCESS",
        "db_assertions": {
            "application_status": "PENDING",
            "applicant_name": "Phuleswari Saikia",
            "block": "Sonari",
            "audit_action": "SUBMIT",
            "portal_user_exists": True,
        },
    },
    {
        "id": "persona_2_bhabesh",
        "name": "Bhabesh Kalita",
        "age": 64,
        "dob": "04/09/1962",
        "gender": "Male",
        "marital_status": "Married",
        "husband_name": "",
        "village": "Koliabor",
        "block": "Rajapara",
        "mobile": "9854022332",
        "bank_account": "30129845671",
        "ifsc": "CBIN0280123",
        "role": "citizen",
        "language_style": "Direct, impatient daily wager who applied earlier and wants an immediate progress update.",
        "dialogue_prompt": (
            "Listen, I am Bhabesh Kalita from Koliabor village, Rajapara block. "
            "I submitted my pension paper 4 days ago at the computer shop. "
            "Tell me what is happening with my application? Is it approved or still lying there?"
        ),
        "intent": "status_check",
        "expected_result": "STATUS_RETRIEVED",
        "db_assertions": {
            "application_status": "PENDING",
            "no_duplicate_created": True,
        },
    },
    {
        "id": "persona_3_tarulata",
        "name": "Tarulata Gogoi",
        "age": 68,
        "dob": "22/11/1957",
        "gender": "Female",
        "marital_status": "Widowed",
        "husband_name": "Late Naren Gogoi",
        "village": "Borbam",
        "block": "Namti",
        "mobile": "9854033443",
        "bank_account_old": "111122223333",
        "bank_account_new": "55556666777788",
        "ifsc": "UBIN0532101",
        "role": "citizen",
        "language_style": "Anxious weaver who realizes she gave the wrong passbook number and needs to cancel and reapply.",
        "dialogue_prompt": (
            "Namaskar babu, I made a grave mistake. Yesterday I submitted my form, but I typed my neighbor's "
            "account number by mistake instead of my own United Bank passbook. "
            "Can I take back my pending application and submit the correct one? My correct account is 55556666777788."
        ),
        "intent": "withdraw_and_reapply",
        "expected_result": "WITHDRAWN_THEN_RESUBMITTED",
        "db_assertions": {
            "first_app_status": "WITHDRAWN",
            "first_decided_by": "APPLICANT",
            "second_app_status": "PENDING",
            "second_bank_account": "55556666777788",
        },
    },
    {
        "id": "persona_4_ramakant",
        "name": "Ramakant Tewari",
        "age": 58,
        "dob": "05/06/1968",
        "gender": "Male",
        "marital_status": "Married",
        "husband_name": "",
        "village": "Rampur",
        "block": "Borgaon",
        "mobile": "9854044554",
        "bank_account": "40987612345",
        "ifsc": "SBIN0004567",
        "role": "citizen",
        "language_style": "Colloquial Bhojpuri/Hindi; farmer mistakenly believing pension threshold is 58 years.",
        "dialogue_prompt": (
            "Pranam sahb, Ramakant Tewari from Rampur, Borgaon. "
            "I turned 58 this summer, born 05/06/1968. Work has become tough in the fields. "
            "Please register my name for the old age pension."
        ),
        "intent": "underage_attempt",
        "expected_result": "VALIDATION_REJECTION",
        "db_assertions": {
            "no_application_created": True,
        },
    },
    {
        "id": "persona_5_minati",
        "name": "Minati Barua",
        "age": 74,
        "dob": "18/01/1952",
        "gender": "Female",
        "marital_status": "Widowed",
        "husband_name": "Late Dhireswar Barua",
        "village": "Charaideo",
        "block": "Sonari",
        "mobile": "9854055665",
        "bank_account": "20349811234",
        "ifsc": "PUNB0123400",
        "role": "citizen",
        "language_style": "Frail grandmother whose application has been stuck for 22 days without departmental action.",
        "dialogue_prompt": (
            "Beta, I am Minati Barua from Charaideo. It has been more than 3 weeks since we submitted my paper in Sonari. "
            "Nobody has approved it yet. What does the government rule say when officers delay so much?"
        ),
        "intent": "sla_inquiry",
        "expected_result": "DEEMED_APPROVAL_FLAGGED",
        "db_assertions": {
            "days_elapsed_gt_15": True,
            "deemed_eligible": True,
        },
    },
    {
        "id": "persona_6_dimbeswar",
        "name": "Dimbeswar Chetia",
        "age": 66,
        "dob": "15/08/1960",
        "gender": "Male",
        "marital_status": "Married",
        "husband_name": "",
        "village": "Moran Pathar",
        "block": "Dhemaji Pathar",
        "mobile": "9854066776",
        "bank_account": "123456789012",
        "ifsc": "BARB0DHEMAJ",
        "role": "citizen",
        "language_style": "Common Service Center (CSC) VLE operator submitting on behalf of a rural elder.",
        "dialogue_prompt": (
            "CSC Operator VLE-44102 reporting. Submitting Old Age Pension for citizen Dimbeswar Chetia, "
            "DOB 15/08/1960 (age 66), residing at Moran Pathar, block Dhemaji Pathar. "
            "Bank of Baroda account 123456789012, IFSC BARB0DHEMAJ. Aadhaar age proof attached. "
            "Please generate official acknowledgment."
        ),
        "intent": "kiosk_submission",
        "expected_result": "SUCCESS_WITH_ACK",
        "db_assertions": {
            "application_status": "PENDING",
            "block": "Dhemaji Pathar",
            "acknowledgment_ready": True,
        },
    },
    {
        "id": "persona_7_arati",
        "name": "Arati Das",
        "age": 62,
        "dob": "10/10/1964",
        "gender": "Female",
        "marital_status": "Married",
        "husband_name": "Prabin Das",
        "village": "Bihpuria",
        "block": "Dispur",  # Invalid block outside pilot scheme
        "mobile": "9854077887",
        "bank_account": "333344445555",
        "ifsc": "SBIN0005555",
        "role": "citizen",
        "language_style": "Urban edge resident asking if she can apply from Dispur block.",
        "dialogue_prompt": (
            "Hello, I am Arati Das, 62 years old, living in Bihpuria in Dispur block. "
            "Can you submit my old age pension application for Dispur?"
        ),
        "intent": "invalid_block_attempt",
        "expected_result": "BLOCK_VALIDATION_ERROR",
        "db_assertions": {
            "no_application_created": True,
        },
    },
    {
        "id": "persona_8_joyprakash",
        "name": "Joyprakash Nath",
        "age": 65,
        "dob": "03/04/1961",
        "gender": "Male",
        "marital_status": "Married",
        "husband_name": "",
        "village": "Gelakey",
        "block": "Khelua",
        "mobile": "9854088998",
        "bank_account": "444455556666",
        "ifsc_invalid": "punb01234",
        "ifsc_valid": "PUNB0012345",
        "role": "citizen",
        "language_style": "Confused about bank passbook IFSC formatting; gets guidance and corrects code.",
        "dialogue_prompt": (
            "Namaste, I am Joyprakash Nath from Gelakey village, Khelua. DOB 03/04/1961. "
            "My bank is Punjab National Bank, account 444455556666. On my cheque book it is written 'punb01234'. "
            "If that is invalid, the branch IFSC is PUNB0012345. Please submit with the correct one."
        ),
        "intent": "ifsc_correction_submission",
        "expected_result": "SUCCESS_WITH_NORMALIZED_IFSC",
        "db_assertions": {
            "application_status": "PENDING",
            "ifsc": "PUNB0012345",
        },
    },
    {
        "id": "persona_9_malati",
        "name": "Malati Medhi",
        "age": 76,
        "dob": "25/12/1949",
        "gender": "Female",
        "marital_status": "Widowed",
        "husband_name": "Late Bipul Medhi",
        "village": "Sepon",
        "block": "Sonari",
        "mobile": "9854099009",
        "bank_account": "777788889999",
        "ifsc": "SBIN0007890",
        "role": "citizen",
        "language_style": "Illiterate widow asking if her pension was officially approved and what the officer wrote.",
        "dialogue_prompt": (
            "Pranam babu, I am Malati Medhi from Sepon. The postman told me my pension was passed by the Sonari office. "
            "Can you check and read me the officer's exact decision and date?"
        ),
        "intent": "approved_inquiry",
        "expected_result": "APPROVED_DETAILS_RETRIEVED",
        "db_assertions": {
            "status": "APPROVED",
            "decided_by_present": True,
        },
    },
    {
        "id": "persona_10_jagannath",
        "name": "Jagannath Bora",
        "age": 63,
        "dob": "01/02/1963",
        "gender": "Male",
        "marital_status": "Married",
        "husband_name": "",
        "village": "Salaguri",
        "block": "Namti",
        "mobile": "9854000110",
        "bank_account": "888899990000",
        "ifsc": "SBIN0009999",
        "role": "citizen",
        "language_style": "Heard a rumor about double pension and tries to submit a duplicate application on his active mobile.",
        "dialogue_prompt": (
            "Hello sir, I am Jagannath Bora, Salaguri, Namti. My neighbor said government is giving a second bonus pension. "
            "Please apply again for my mobile 9854000110."
        ),
        "intent": "duplicate_prevention",
        "expected_result": "DUPLICATE_REJECTED",
        "db_assertions": {
            "no_second_row_created": True,
        },
    },
]

OFFICER_PERSONAS = [
    {
        "id": "officer_1_sonari",
        "name": "Anurag Sharma (BDO Sonari)",
        "username": "bdo_sonari",
        "role": "officer",
        "jurisdiction": "Sonari",
        "dialogue_prompt": (
            "Check the pending application for Phuleswari Saikia (mobile 9854011221). "
            "Inspect her age proof document and approve the application with justification: "
            "'Aadhaar verified age 71, valid SBI account in Sonari block. Approved under Purvanchal RTPS Act.'"
        ),
        "intent": "officer_approval",
        "expected_result": "APPROVED_SUCCESS",
    },
    {
        "id": "officer_2_rajapara",
        "name": "Priyanka Neog (BDO Rajapara)",
        "username": "bdo_rajapara",
        "role": "officer",
        "jurisdiction": "Rajapara",
        "dialogue_prompt": (
            "Search for overdue applications in Rajapara block older than 15 days, "
            "and inspect block-level statistics."
        ),
        "intent": "officer_queue_monitoring",
        "expected_result": "STATS_AND_OVERDUE_RETRIEVED",
    },
]
