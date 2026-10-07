I want to write a demo phone app for my new project name - "URBAN CHILDHOOD", it is a Parental Guidance System designed to support parents at every stage of their child’s development.
I want to create app for demo purposes only.
Software purpose:
    This mobile application aims to address parents’ anxieties and concerns about their children by helping them understand their child’s growth, behavior, and developmental stages through clear guidance and practical advice
    
page 1: Login Page (SSO login, google account login, microsoft account login) (need forgot password and create new SSO login button)
page 2: create a Kid Avartar space
Purpose: the 3D Avartar cartoon represent their kid, once completed the input for the avartar for creation, this avartar will grow up day by day following the real time.
1. show all available Avartar cartoon in "Kid Avartar space"
2. two button at the bottom:
* button_1 = "Let's GO" [validation, must select atleast one avartar] 
* button_2 = "Create Avartar" 
3. If button_1, then redirect into menu lobby.
If button_2, then display avartar edit page to create the avartar with (name,gender,age,race,skin colour,hair colour,Allergy Notes).

page 3: Menu lobby
- Differentiate by multiple tab of design.
- Tab bar show at the bottom with different categorizes
a. Home
b. Know Your Kid’s Developmental Stage
c. Lets Do IT
d. Nutrition Advice
e. What’s Next for Your Baby
f. Me (similar to user profile)

for demo purposes, each tab with empty page.

page 4: Home
split by two layers
 
Layer 1 (header) (30 percent of entire page height) (including the tab bar)
1. TOP side: 
logo + Title (URBAN CHILDHOODS)

2. Bottom left side:
- if login as guest, then = Label ("Hi,\nDear Mummy and Daddy")
- if login as member, then = Label ("Hi,\nAwasome [depending the registered account is male or female to display mummy or daddy]")
3. Bottom right side: 
- QR code (when parents want to visit our physical shop, they just need to show the QR code)

Layer 2(Information layer) (70 percent of entire page height) (including the tab bar)
1. Presentation view: show row box by row box
mainly for our official announcement, promotion news, training, event info, and so on


Page 5: Know Your Kid’s Developmental Stage
Description:
This feature helps parents better understand their child’s behavior and developmental stage.
The system provides guidance and tips based on the child’s current needs, categorized into the following areas:
1. Social & Emotional
2. Language and Communication
3. Brain Development
4. Movement and Physical Development
5. Food and Nutrition
6. Things for Parents to Look Out For

no input needed for this screen, because while create the avartar, 
it already declared the age of the kid/baby.
we shall allow parent to choose which needs they want.

present the option in boxes (like operation system microsoft UI design)
1. Overall
2. Social & Emotional
3. Brain Development
4. Movement & Physical Development
5. Food & Nutrition
6. Things for Parents to Look Out For

Example: 6-Month-Old Baby
Social & Emotional
- How your baby connects with people around them at 6 months
- Usually happy and responsive to others’ emotions
- Begins to distinguish between familiar faces and strangers
- Enjoys playing with parents and caregivers
- Likes looking at their reflection in a mirror
Tips for Parents:
- Talk to your baby about what is happening around them using a gentle and positive tone
- Include a child-safe mirror among their toys so they can observe their movements
- Play interactive games such as peek-a-boo

Brain Development
- How your baby’s brain is growing
- Shows curiosity by reaching for nearby and out-of-reach objects
- Transfers objects from one hand to the other and brings them to the mouth
Tips for Parents:
- Provide toys that are easy to grasp with one hand
- Talk about the objects your baby is holding or mouthing

Movement & Physical Development
- How your baby moves through their environment
- Begins sitting without support
- Rolls over in both directions
- Pushes down on their legs when feet are on a firm surface
- Rocks back and forth
Tips for Parents:
- Place favorite toys nearby to encourage rolling and reaching

Food & Nutrition
- What mealtimes look like at 6 months
- Shows interest in food and opens their mouth when spoon-fed
- Moves food from the front to the back of the mouth
- Begins eating cereals and single-ingredient purees (e.g., carrots, sweet potato, pears)
Tips for Parents:
- At 6 months, breast milk alone is no longer sufficient. Introduce 2–3 spoonfuls of soft food, up to four times a day

Things for Parents to Look Out For
(Consult a paediatrician if your 6-month-old baby:)
- Does not show affection toward parents or caregivers
- Does not respond to nearby sounds
- Rarely laughs
- Has difficulty bringing objects to their mouth
- Does not make vowel sounds
- Appears unusually floppy or stiff
- Cannot roll over in either direction
- Does not attempt to reach for nearby objects

B. Lets Do IT tab requirement:
Description:
Based on the baby’s current developmental stage, the system provides guidance on what the child can begin learning across different developmental areas.

UI:
Layer 1:
1. Button A - Label "PLAN For Baby"
Description: Do not know what to do Mummy/Daddy? Let's us advice YOU :)

Layer 2: (Plan List)
Usage: this list is depending the age of the baby to advice what he/she can do now with one week activity.
Condition: 
1. Default to hide this list if user didn't click on "Button A"
2. Give an exit icon button for user to close the plan list.
UI: show in an interesting list for parent to see (user experience)
as demo version, please put as below sample:
Day 1: Sweet Touch with ME (Social & Emotional Development)
total of 30 min
10 min - Mummy & Daddy, Talk to me what's happening today.
10 min - Play interactive games such as peek-a-boo.
10 min - Hug games corss-over with Mummy and Daddy.

Day 2: Make a MOVE (Movement & Physical Development)
total of 30 min
10 min - Tummy Time (Continue daily tummy time to strengthen neck, back, and core muscles needed for sitting and crawling)
5 min - Supported Sitting (Practice sitting with support to build balance and core strength)
10 min - Grasping & Transferring Objects (Offer safe, easy-to-hold toys to encourage reaching and hand-to-hand transfer)
5 min - Weight Bearing (Allow the baby to push down on their legs while being securely supported)

day 3, 4, 5, 6, 7... and so on
   
Layer 3: (FREE a Pick)
this layer to allow users to pick what they want their baby to do in random.
UI: show each of the activity in box UI (like a microsoft boxes)

Example of things to do as below:
Physical & Motor Skills
- Tummy Time: Continue daily tummy time to strengthen neck, back, and core muscles needed for sitting and crawling
- Supported Sitting: Practice sitting with support to build balance and core strength
- Grasping & Transferring Objects: Offer safe, easy-to-hold toys to encourage reaching and hand-to-hand transfer
- Weight Bearing: Allow the baby to push down on their legs while being securely supported

Communication & Language Skills
- Engage in “Conversations”: Respond to babbling using real words to encourage turn-taking
- Talk and Narrate: Describe daily activities and surroundings
- Read Together: Use colorful board or cloth books and name objects
- Sing Songs and Rhymes: Use action-based songs to promote rhythm and interaction

Cognitive & Social Skills
- Peek-a-Boo: Helps develop object permanence and social bonding
- Mirror Play: Encourages self-awareness and facial recognition
- Explore Textures: Provide safe objects with different textures
- Introduce Solids and a Cup: Support early feeding skills when readiness signs appear




C. Nutrition Advice
1. Continue Milk Feeds:
- Breast milk or iron-fortified formula should remain the main drink
2. Prioritize Iron-Rich Foods:
- Iron-fortified cereals
- Pureed or finely minced meat, poultry, and fish
- Mashed legumes or tofu
3. Offer a Variety of Foods:
- Introduce different food groups to support nutrition and reduce picky eating
4. Introduce Allergenic Foods Early:
- Introduce common allergens one at a time from around 6 months
5. Focus on Texture Progression:
- Gradually move from purees to mashed, minced, and finger foods
6. Avoid Harmful Foods & Drinks:
- No honey before 12 months
- No added salt or sugar
- Avoid unsuitable drinks and choking hazards
7. Offer Water:
- Provide sips of cooled, boiled water during meals
8. Watch for Hunger & Fullness Cues:
- Allow the baby to guide how much they eat


D. What’s Next for Your Baby?
Description:
The next stage focuses on rapid growth in mobility, communication, and social interaction as your baby becomes an active explorer.
1. Enhanced Safety Measures (Babyproofing)
- Secure cabinets, outlets, stairs, and furniture
- Maintain constant supervision
2. Food Texture Progression & Self-Feeding
- Introduce more textured foods
- Encourage self-feeding and cup use
- Establish regular meal routines
3. Increased Communication & Social Interaction
- Engage in daily conversations and reading
- Respond consistently to gestures and cues
- Prepare for separation anxiety around 8–9 months
4. Preparation for Sleep Changes
- Maintain a consistent bedtime routine
- Support self-soothing during developmental changes

