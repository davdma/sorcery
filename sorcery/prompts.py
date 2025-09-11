summarize = """*Briefly* summarize this partial sequence of scenes in a text adventure RPG game that involves a narrator's description of events, followed by user/player response to choices. Include less detail about older scenes and more detail about the most recent scenes. Also start a new paragraph in the summary for every scene.

For example, if given the scene:
-------------------
# Narrator
You make your way through the lively marketplace toward a colorful fruit stand. The scent of ripe apples, plump berries, and fragrant citrus fills the air, enticing your senses. The vendor, a jovial man with a bushy mustache, greets you with a broad smile. “Ahoy there! Care for some of Eldergrove’s finest? Freshly harvested this morning!” He gestures proudly to the display before him, where baskets overflowing with vibrant produce glisten in the sunlight. Bright red apples, deep blue berries, and sunny oranges all tempt you with their freshness. Feeling a twinge of hunger, you consider your options. Despite your lack of gold, you recall tales of trade where goods can be exchanged for other goods or services. Perhaps this man would be open to an offer beyond coins. “Would you like to try something, young adventurer?” he asks, noticing your keen interest. You feel the warmth of the sun on your skin and look over the tempting fruits, pondering what you might say:
1. Inquire about the prices of the fruits first, hoping there may be something affordable that you can buy with gold you don’t have.
2. Ask the vendor if he has any need for assistance, offering to help in exchange for a piece of fruit.
3. Politely decline purchasing any fruit, preferring to simply enjoy the sights and sounds of the market for now.

# Player
Player action: Inquire about the fruits
-------------------

Then the summary should be like:
The adventurer moves through the market to a fruit stand, tempted by its aroma. He is greeted by a jovial vendor with a bushy mustache. The player is low on gold so asks about the prices hoping for something affordable.

Reminder:
This is only part of a longer sequence of scenes so *DO NOT* conclude the summary with language like "Finally, ...". Because the story continues after the summary.
The summary *MUST* include the relevant character names, places, actions, all info pertinent to the player, and key developments in the plot. Keep necessary details (descriptions e.g. the vendor has a bushy mustache) and facts while eliminating the literary fluff. This way reconstruction will be consistent if past events needs to be recalled in later scenes. The summary should aim to leave zero ambiguity in all plot points.
At the end of each scene do not summarize the options given to the player, only the action the player chooses.
"""

summary_prefix = "A summary of previous events:\n"
