# Grammar based String Generator

This project provides the ability to **generate** strings based on user created grammars
that are similar in form to Parsing Expression Grammars; therefore, this project can be
thought of as the inverse of a parser.

## Example

**Create a Grammar:**

```plain
root = "Hello" , ("World" | "Venus" | "Mars" | "Pluto");
```

This says to generate the word `"Hello"` followed by one of the planet names.

**Run the String Generator (Format: Sentence):**

```bash
mackenzie@caprica: grammar_based_string_generator -s -f example.txt
Hello World
mackenzie@caprica:
```

Note that you can set or remove the delimiter via `-d "something"`.

**Run the String Generator (Format: JSON):**

```bash
mackenzie@caprica: grammar_based_string_generator -f example.txt
["Hello", "Venus"]
mackenzie@caprica:
```

## Grammar of Grammars

**Rules:**
+ **Sequence Rule:** `<operand-0> , ... , <operand-N>`
+ **Choice Rule:** `<operand-0> | ... | <operand-N>`
+ **Repetition Rule:** `<operand> { <minimum> , <maximum> }`
+ **Optional Rule:** `<operand> ?`
+ **Bounded Zero Or More Rule:** `<operand> * <maximum>`
+ **Bounded One Or More Rule:** `<operand> + <maximum>`
+ **Nested Rules:** `( <operand> )`
+ **String Rule:** `"<string-of-text>"`
+ **Named Rule:** `<name> = <operand>`

**Comments:**

Python like single line comments are supported, such as: `# This is a comment!`

## More Extensive Example

**Grammar:**

```plain

# The generated sentence will either be a greeting,
# a goodbye, or describe an attribute of the planet.
Root = Greeting | Goodbye | Mass | Distance | Radius;

# A greeting is the word hello followed by the planet's name;
# Optionally, a subgreeting will be generated for the moon.
# Note the parentheses are only for clarity here.
Greeting = "Hello" , Planet , (MoonGreeting ?);

# There are three types of planets to choose from.
Planet = Terrestrial | Jovian | Former;

# There are four terrestrial planets to choose from.
Terrestrial = "Mercury" | "Venus" | "Earth" | "Mars";

# There are four jovian planets to choose from.
Jovian = "Jupiter" | "Saturn" | "Uranus" | "Neptune";

# Pluto will always be a planet in our hearts.
Former = "Pluto";

# The moon greeting is just a sentence fragment.
# Notice that the word "little" is only included sometimes.
MoonGreeting = "and", "its", "little" ?, "moon";

# A good byte is the word goodbye followed by the planet's name.
Goodbye = "Goodbye" , Planet;

# A description of the planet's radius will include
# the word "very" repeated between zero and three times,
# because the "* 3" means repeat [0..3] times.
Radius = Planet , "is" , ("very" * 3) , "wide";

# A description of the planet's mass will include
# the word "very" repeated between one and three times,
# because the "+ 3" means repeat [1..3] times.
Mass = Planet , "is" , ("very" + 3) , "large";

# A description of the planet's distance will include
# the word "very" repeated between two and five times,
# because the "{ 2, 5 }" means repeat [2..5] times.
Distance = Planet, "is" , ("very" { 2, 5 }) , "far", "away";
```

**Run the String Generator (Format: Sentence):**

```bash
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Pluto is very very large
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Jupiter is very very very large
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Earth is very very very very very far away
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Hello Pluto
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Pluto is very very very far away
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Pluto is very very very large
mackenzie@caprica: grammar_based_string_generator -s -f ~/tmp/string.txt
Hello Pluto and its moon
mackenzie@caprica:
```

## Runtime Limits

Because of the inherently recursive nature of some grammars, a stackoverflow may occur.
In order to prevent stackoverflows of python itself, set `--max-depth <size>`.
Note that the value is may not exactly match the stack height.

Grammars can potentially generate extremely large strings, which overflow memory.
In order to prevent memory exhaustion of python itself, set `--max-length <size>`.
Note that the value is may not exactly match the length of the generated string.
