# slugify drops accented characters ("Café Münster" -> "caf-m-nster")

When I call `slugify("Café Münster")` I expect `cafe-munster` but get `caf-m-nster`.
The regex in `slugify` strips every non a-z0-9 character, including letters with diacritics.
Expected: transliterate accents to ASCII before stripping.
