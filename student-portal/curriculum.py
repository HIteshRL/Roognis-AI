"""
Ghost curriculum — ICSE Class 10, 8 subjects with chapters.

Each chapter carries a short block of factual ICSE-style content. That content is
the *only* thing the tutor is allowed to answer from (per chapter), so retrieval,
concept-grounding and answers are all grounded in it.
"""

SUBJECTS = [
    {
        "id": "physics", "name": "Physics", "icon": "⚛️", "color": "#3949ab",
        "chapters": [
            {"id": "phy-energy", "title": "Force, Work, Power and Energy",
             "summary": "Work, energy, power and their conservation.",
             "content": (
                "Work is done when a force moves a body in the direction of the force; work equals "
                "force multiplied by displacement, and its SI unit is the joule. Power is the rate of "
                "doing work and its unit is the watt. Energy is the capacity to do work. Kinetic energy "
                "is one half m v squared, and gravitational potential energy is m g h. The law of "
                "conservation of energy states that energy can neither be created nor destroyed, only "
                "transformed from one form to another.")},
            {"id": "phy-light", "title": "Refraction of Light through Lenses",
             "summary": "Convex and concave lenses, focal length and magnification.",
             "content": (
                "Refraction is the bending of light as it passes from one transparent medium to another "
                "of different optical density. A convex lens converges parallel rays to a principal focus, "
                "while a concave lens diverges them. The focal length is the distance between the optical "
                "centre and the principal focus. The power of a lens is the reciprocal of its focal length "
                "in metres, measured in dioptres. Magnification is the ratio of image distance to object "
                "distance.")},
            {"id": "phy-current", "title": "Current Electricity",
             "summary": "Ohm's law, resistance and electrical power.",
             "content": (
                "Ohm's law states that the current flowing through a conductor is directly proportional "
                "to the potential difference across it, provided temperature stays constant, so V equals I "
                "times R. Resistances in series add directly, while in parallel the reciprocals of the "
                "resistances add. Electrical power is the product of voltage and current, and can also be "
                "written as I squared R. Electrical energy consumed is measured in kilowatt hours.")},
            {"id": "phy-sound", "title": "Sound",
             "summary": "Longitudinal waves, echoes and resonance.",
             "content": (
                "Sound is a longitudinal mechanical wave that needs a material medium to travel and cannot "
                "pass through a vacuum. Loudness depends on the amplitude of the wave and pitch depends on "
                "its frequency. An echo is the reflection of sound from a distant surface; to hear a "
                "distinct echo the reflecting surface must be at least seventeen metres away. Resonance "
                "occurs when the frequency of a forced vibration equals the natural frequency of a body.")},
        ],
    },
    {
        "id": "chemistry", "name": "Chemistry", "icon": "🧪", "color": "#00897b",
        "chapters": [
            {"id": "chem-periodic", "title": "The Periodic Table",
             "summary": "Periodic law and trends across periods and groups.",
             "content": (
                "Mendeleev arranged elements in order of increasing atomic mass, but the modern periodic "
                "law arranges them by increasing atomic number. Across a period from left to right, atomic "
                "size decreases while non-metallic and electronegative character increases. Down a group, "
                "atomic size increases and metallic character increases because new shells are added. "
                "Elements in the same group have similar chemical properties.")},
            {"id": "chem-acids", "title": "Acids, Bases and Salts",
             "summary": "pH scale, neutralisation and types of salts.",
             "content": (
                "Acids release hydrogen ions in aqueous solution and turn blue litmus red, while bases "
                "release hydroxide ions and turn red litmus blue. The pH scale runs from zero to fourteen; "
                "below seven is acidic, seven is neutral and above seven is basic. Neutralisation is the "
                "reaction of an acid with a base to give a salt and water. Salts may be normal, acid or "
                "basic depending on the ions they contain.")},
            {"id": "chem-mole", "title": "Mole Concept and Stoichiometry",
             "summary": "Avogadro's number, molar mass and gas volumes.",
             "content": (
                "One mole of any substance contains Avogadro's number of particles, which is six point "
                "zero two two times ten to the power twenty three. The molar mass is the mass of one mole "
                "expressed in grams. Gay-Lussac's law states that gases react in simple whole number "
                "ratios of their volumes at the same temperature and pressure. The empirical formula gives "
                "the simplest whole-number ratio of atoms in a compound.")},
            {"id": "chem-electrolysis", "title": "Electrolysis",
             "summary": "Decomposition of electrolytes by electric current.",
             "content": (
                "Electrolysis is the decomposition of an electrolyte by the passage of an electric current "
                "through it. Positively charged cations move towards the cathode where reduction occurs, "
                "and negatively charged anions move towards the anode where oxidation occurs. The "
                "electrolysis of acidified water liberates hydrogen at the cathode and oxygen at the "
                "anode in a two to one ratio by volume.")},
        ],
    },
    {
        "id": "biology", "name": "Biology", "icon": "🧬", "color": "#1e8e3e",
        "chapters": [
            {"id": "bio-celldiv", "title": "Cell Division",
             "summary": "Mitosis and meiosis and their stages.",
             "content": (
                "Cell division occurs by mitosis and meiosis. Mitosis produces two genetically identical "
                "diploid daughter cells and is responsible for growth and repair. Meiosis produces four "
                "genetically different haploid cells and forms the gametes for sexual reproduction. The "
                "main stages of division are prophase, metaphase, anaphase and telophase. DNA is "
                "duplicated during the interphase before division begins.")},
            {"id": "bio-photo", "title": "Photosynthesis",
             "summary": "How green plants make food using light.",
             "content": (
                "Photosynthesis is the process by which green plants make glucose from carbon dioxide and "
                "water using light energy trapped by the green pigment chlorophyll, releasing oxygen as a "
                "by-product. It takes place mainly in the chloroplasts of leaf cells. The process has a "
                "light-dependent phase and a light-independent phase. The glucose formed stores chemical "
                "energy for the plant.")},
            {"id": "bio-circulation", "title": "The Circulatory System",
             "summary": "Heart, blood vessels and double circulation.",
             "content": (
                "The human heart is a four-chambered muscular pump with two atria and two ventricles. The "
                "left side pumps oxygenated blood to the body while the right side pumps deoxygenated blood "
                "to the lungs. Arteries carry blood away from the heart and have thick elastic walls, while "
                "veins carry blood back to the heart and contain valves. In double circulation blood passes "
                "through the heart twice in one complete cycle.")},
            {"id": "bio-excretion", "title": "The Excretory System",
             "summary": "Kidneys, nephrons and urine formation.",
             "content": (
                "Excretion removes nitrogenous waste from the body. The kidneys are the main excretory "
                "organs and the nephron is the functional unit of the kidney. Urine is formed in three "
                "steps: ultrafiltration in the glomerulus, selective reabsorption of useful substances, and "
                "tubular secretion. The chief nitrogenous waste excreted by humans is urea.")},
        ],
    },
    {
        "id": "maths", "name": "Mathematics", "icon": "📐", "color": "#1967d2",
        "chapters": [
            {"id": "math-quad", "title": "Quadratic Equations",
             "summary": "Solving quadratics and the discriminant.",
             "content": (
                "A quadratic equation has the standard form a x squared plus b x plus c equals zero, where "
                "a is not zero. It can be solved by factorisation, by completing the square, or by using "
                "the quadratic formula x equals minus b plus or minus the square root of b squared minus "
                "four a c, all divided by two a. The discriminant b squared minus four a c decides the "
                "nature of the roots.")},
            {"id": "math-ap", "title": "Arithmetic Progression",
             "summary": "nth term and sum of an AP.",
             "content": (
                "An arithmetic progression is a sequence in which each term differs from the previous term "
                "by a fixed number called the common difference. The nth term of an AP is a plus n minus "
                "one times d, where a is the first term. The sum of the first n terms is n by two into "
                "twice a plus n minus one times d.")},
            {"id": "math-gst", "title": "Goods and Services Tax",
             "summary": "GST, CGST, SGST, IGST and input tax credit.",
             "content": (
                "Goods and Services Tax is an indirect tax levied on the supply of goods and services. For "
                "sales within a state it is divided equally into Central GST and State GST, while for sales "
                "between states an Integrated GST is charged. A registered dealer can claim input tax "
                "credit, deducting the tax already paid on purchases from the tax collected on sales.")},
            {"id": "math-trig", "title": "Trigonometry",
             "summary": "Ratios, identities and heights and distances.",
             "content": (
                "In a right-angled triangle the sine of an angle is the opposite side over the hypotenuse, "
                "the cosine is the adjacent side over the hypotenuse, and the tangent is the opposite over "
                "the adjacent. For complementary angles the sine of an angle equals the cosine of its "
                "complement. Problems on heights and distances use the angle of elevation and the angle of "
                "depression.")},
        ],
    },
    {
        "id": "history", "name": "History & Civics", "icon": "🏛️", "color": "#e8710a",
        "chapters": [
            {"id": "his-1857", "title": "The First War of Independence, 1857",
             "summary": "Causes, leaders and results of the 1857 revolt.",
             "content": (
                "The First War of Independence of eighteen fifty seven was triggered by the introduction of "
                "the greased cartridges of the Enfield rifle, which offended both Hindu and Muslim soldiers. "
                "Prominent leaders of the revolt included Mangal Pandey, Rani Lakshmibai of Jhansi, Tantia "
                "Tope and Nana Sahib. Although the revolt failed, it ended the rule of the East India "
                "Company and brought India under the direct control of the British Crown.")},
            {"id": "his-nationalism", "title": "The Rise of Nationalism",
             "summary": "Congress, Moderates, Assertives and Swadeshi.",
             "content": (
                "The Indian National Congress was founded in eighteen eighty five and became the main "
                "platform of the national movement. The early leaders, called Moderates, used petitions and "
                "constitutional methods, while the later Assertives such as Bal Gangadhar Tilak demanded "
                "Swaraj or self-rule. The partition of Bengal in nineteen zero five led to the Swadeshi "
                "Movement, which encouraged the use of Indian-made goods.")},
            {"id": "his-mass", "title": "Mass Movements under Gandhi",
             "summary": "Non-Cooperation, Civil Disobedience and Quit India.",
             "content": (
                "Mahatma Gandhi led three great mass movements using satyagraha and non-violence. The "
                "Non-Cooperation Movement of nineteen twenty asked Indians to boycott British goods, "
                "titles and institutions. The Civil Disobedience Movement of nineteen thirty began with the "
                "Dandi Salt March against the salt law. The Quit India Movement of nineteen forty two "
                "demanded an immediate end to British rule.")},
            {"id": "his-parliament", "title": "The Union Legislature",
             "summary": "Lok Sabha, Rajya Sabha and how a bill becomes law.",
             "content": (
                "The Union Legislature of India, called Parliament, consists of the President and two "
                "houses. The Lok Sabha is the House of the People whose members are directly elected, while "
                "the Rajya Sabha is the Council of States whose members represent the states. A bill "
                "becomes an Act only after it is passed by both houses and receives the assent of the "
                "President.")},
        ],
    },
    {
        "id": "geography", "name": "Geography", "icon": "🗺️", "color": "#d93025",
        "chapters": [
            {"id": "geo-climate", "title": "Climate of India",
             "summary": "Monsoon climate and factors affecting it.",
             "content": (
                "India experiences a tropical monsoon type of climate. The south-west monsoon, blowing from "
                "June to September, brings the greater part of the country's annual rainfall. The main "
                "factors that affect the climate of India are latitude, altitude, distance from the sea, "
                "and the relief or physical features of the land. The retreating monsoon brings rain to the "
                "Coromandel coast.")},
            {"id": "geo-soil", "title": "Soil Resources",
             "summary": "Alluvial, black, red and laterite soils.",
             "content": (
                "The major soil types of India are alluvial soil, black soil, red soil and laterite soil. "
                "Alluvial soil is the most fertile and is found in the northern plains, deposited by rivers. "
                "Black soil, also called regur, is rich in clay and is ideal for growing cotton. Soil "
                "erosion can be prevented by afforestation, terrace farming and building bunds.")},
            {"id": "geo-water", "title": "Water Resources and Irrigation",
             "summary": "Irrigation methods and rainwater harvesting.",
             "content": (
                "Irrigation is the artificial supply of water to crops. The common means of irrigation in "
                "India are wells and tube-wells, canals, and tanks. Rainwater harvesting is the collection "
                "and storage of rainwater to recharge groundwater and conserve water. Multipurpose river "
                "valley projects provide irrigation, hydroelectric power and flood control together.")},
            {"id": "geo-industry", "title": "Minerals and Industries",
             "summary": "Mineral resources and industrial location.",
             "content": (
                "India possesses important minerals such as iron ore, manganese, bauxite and coal. "
                "Industries are broadly classified as agro-based industries, such as cotton textiles, and "
                "mineral-based industries, such as iron and steel. The location of an industry depends on "
                "the availability of raw materials, power, labour, capital and transport.")},
        ],
    },
    {
        "id": "english", "name": "English Literature", "icon": "📖", "color": "#9334e6",
        "chapters": [
            {"id": "eng-poetry", "title": "Poetry and Literary Devices",
             "summary": "Metaphor, simile, personification and more.",
             "content": (
                "Poetry uses figures of speech to create vivid images. A simile compares two things using "
                "the words like or as, while a metaphor is an implied comparison that states one thing is "
                "another. Personification gives human qualities to non-living things or ideas. Alliteration "
                "is the repetition of the same initial consonant sound in nearby words, and the rhyme "
                "scheme is the pattern of rhyming sounds at the ends of lines.")},
            {"id": "eng-merchant", "title": "Drama — The Merchant of Venice",
             "summary": "Justice, mercy and appearance versus reality.",
             "content": (
                "The Merchant of Venice by William Shakespeare centres on a bond between the merchant "
                "Antonio and the moneylender Shylock, who demands a pound of flesh. Portia, disguised as a "
                "young lawyer, saves Antonio and delivers the famous speech on the quality of mercy. The "
                "play explores the themes of justice versus mercy and appearance versus reality.")},
            {"id": "eng-story", "title": "Elements of the Short Story",
             "summary": "Plot, character, setting and theme.",
             "content": (
                "A short story is a brief work of fiction with a single plot, a few characters and a clear "
                "setting. Its plot usually moves through exposition, rising action, climax, falling action "
                "and resolution. The setting is the time and place of the action, and the theme is the "
                "central idea or message that the writer wishes to convey to the reader.")},
            {"id": "eng-writing", "title": "Comprehension and Composition",
             "summary": "Reading skills and structured writing.",
             "content": (
                "Comprehension tests a reader's ability to understand a passage and answer questions in "
                "their own words. Good composition, whether a story, an essay or a letter, needs a clear "
                "structure with an introduction, a body and a conclusion. Effective writing depends on "
                "correct grammar, coherence between ideas, and the use of appropriate and varied "
                "vocabulary.")},
        ],
    },
    {
        "id": "computers", "name": "Computer Applications", "icon": "💻", "color": "#455a64",
        "chapters": [
            {"id": "cs-classes", "title": "Classes and Objects in Java",
             "summary": "Blueprints, instances and object orientation.",
             "content": (
                "Java is an object-oriented programming language. A class is a blueprint or template that "
                "defines the data members, which store the state, and the methods, which define the "
                "behaviour. An object is an instance of a class created using the new keyword. Encapsulation "
                "binds data and methods together and hides the internal details of an object.")},
            {"id": "cs-constructor", "title": "Constructors",
             "summary": "Initialising objects with constructors.",
             "content": (
                "A constructor is a special member method that is used to initialise an object when it is "
                "created. It has the same name as the class and has no return type, not even void. A default "
                "constructor takes no arguments, whereas a parameterised constructor accepts arguments to "
                "set the initial values. Constructors can be overloaded by changing the number or type of "
                "their parameters.")},
            {"id": "cs-loops", "title": "Iterative Constructs",
             "summary": "for, while and do-while loops.",
             "content": (
                "An iterative construct or loop repeats a block of statements a number of times. Java "
                "provides the for loop, the while loop and the do-while loop. The for and while loops are "
                "entry-controlled loops that test the condition before executing the body, while the "
                "do-while loop is exit-controlled and executes its body at least once. The break statement "
                "exits a loop and continue skips to the next iteration.")},
            {"id": "cs-arrays", "title": "Arrays",
             "summary": "Storing many values under one name.",
             "content": (
                "An array is a collection of elements of the same data type stored under a single name and "
                "accessed by an index. The index of an array begins at zero, so the first element is at "
                "index zero. A single dimensional integer array of size five is declared as int square "
                "bracket a equals new int five. The length of an array is fixed once it is created.")},
        ],
    },
]

# Fast lookups
SUBJECT_BY_ID = {s["id"]: s for s in SUBJECTS}
CHAPTER_BY_ID = {c["id"]: c for s in SUBJECTS for c in s["chapters"]}
CHAPTER_SUBJECT = {c["id"]: s["id"] for s in SUBJECTS for c in s["chapters"]}
