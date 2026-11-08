# UX/UI Quality

[Русский](README.ru.md) · [Skill](skills/ux-ui-quality/SKILL.md) · [License](LICENSE)

A Codex skill for making the right size of UX/UI improvement. Fix a confusing control by checking its affected states; review a whole journey when the task changes how people finish their work. The skill helps Codex make that distinction on websites, web apps, and native apps.

- **Start with the user's task.** Check what people need to see, do, and verify, including recovery from a relevant error.
- **Match the review to the change.** A button fix calls for a local check. A risky or unfamiliar workflow calls for more evidence.
- **Check what happened.** For material visual changes, exercise the affected scenarios in the rendered interface. Record unverified states and limits.

## Try it

With a Codex CLI that supports plugin marketplaces:

~~~sh
codex plugin marketplace add alexandryasukaitisss-cmd/ux-ui-quality
codex plugin add ux-ui-quality@ux-ui-quality
codex plugin list --marketplace ux-ui-quality
~~~

Then ask: **“Use $ux-ui-quality. Explain why this submit button is disabled. Check the affected states.”** Codex can also select the skill when its description matches a task. The skill instructions and references are in Russian; you can give the task in English.

The plugin ships a skill and references. It has no runtime service, MCP server, or install hook. The catalogue's authentication field belongs to the marketplace format; the plugin itself has no sign-in.

## What's inside

[32 rules](skills/ux-ui-quality/references/principles.md) with triggers, checks, and limits; [journey examples](skills/ux-ui-quality/references/journeys.md); [product patterns](skills/ux-ui-quality/references/product-patterns.md); [71 sources](skills/ux-ui-quality/references/sources.json) with dates and scope. The [evaluation cases](evals/cases.json) and [regressions](evals/regressions.json) are reusable prompts and rubrics.

~~~sh
python3 -B -m unittest discover -s tests -v
~~~

The tests check structure, links, source references, and rubric integrity. They do not measure the effect on a model's design decisions. See [attribution](NOTICE.md).
