#question-schema

question-identifier=string
has_internal_choice=boolean
primary_question=string
secondary_question=string/can be null

diagram_url=cloudinary-url
table_url=cloudinary-url
primary_marks=string
secondary_marks=string/can be null

question_type=Subjective/MCQ/Assertion Reasoning/Case Based

Note:

1. secondary question can be null since it will only be populated if has_internal_choice is true.
2. Here the question_type is also Choice based but is not written explicitely because has_intenal_choice boolean will store the exact same inforamtion.
