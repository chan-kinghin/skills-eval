# SkillEval Launch Checklist

Checklist of platforms, optimizations, and actions for launching SkillEval publicly.

---

## GitHub Repository Optimization

- [ ] **Repository description**: "Find the cheapest LLM that gets your task 100% right. CLI tool for automated model evaluation on deterministic tasks."
- [ ] **Topics/tags**: `llm`, `llm-evaluation`, `model-selection`, `cost-optimization`, `cli`, `python`, `openai-compatible`, `benchmark`, `nlp`, `automation`
- [ ] **Social preview image**: Create a 1280x640 image showing the tool name, tagline, and a sample results table. Use a dark background with terminal-style font for the results.
- [ ] **Pin the repo** on your GitHub profile
- [ ] **Add "About" sidebar links**: Link to User Manual and blog post
- [ ] **Releases**: Create a v0.1.0 release with a changelog summarizing all features
- [ ] **Issue templates**: Add templates for bug reports and feature requests
- [ ] **Discussion tab**: Enable Discussions for Q&A and show-and-tell

---

## English-Language Platforms

### Dev Blogs

- [ ] **dev.to** -- Publish the blog post (see `BLOG_POST.md`). Add tags: `llm`, `python`, `opensource`, `ai`. Publish early morning US Pacific time (8-10 AM) for best visibility.
- [ ] **Medium** -- Cross-post the blog post. Submit to publications: "Towards Data Science", "Better Programming", or "Level Up Coding" for wider reach.
- [ ] **Hashnode** -- Cross-post with canonical URL pointing to dev.to or your own blog.

### Community Forums

- [ ] **Hacker News** -- Submit as "Show HN" post (see `SOCIAL_MEDIA.md`). Best times: Tuesday-Thursday, 8-10 AM US Eastern. Keep the title factual and concise.
- [ ] **Reddit r/MachineLearning** -- Post as a [Project] thread. Follow subreddit rules about self-promotion.
- [ ] **Reddit r/LocalLLaMA** -- Emphasize the `--endpoint` flag for testing local models. This community appreciates tools that work with Ollama and local inference.
- [ ] **Reddit r/Python** -- Focus on the CLI design, async architecture, and developer experience.
- [ ] **Reddit r/LanguageTechnology** -- Brief post focusing on the NLP evaluation angle.

### Social Media

- [ ] **Twitter/X** -- Post the thread (see `SOCIAL_MEDIA.md`). Pin the first tweet. Space out tweets by 2-3 minutes for readability in timelines.
- [ ] **LinkedIn** -- Post the LinkedIn version (see `SOCIAL_MEDIA.md`). Tag relevant connections. Best times: Tuesday-Thursday, 8-10 AM local time.

### Product Directories

- [ ] **Product Hunt** -- Launch with tagline and description from `SOCIAL_MEDIA.md`. Best day: Tuesday or Wednesday. Prepare 3-4 screenshots showing catalog, results table, and HTML report.
- [ ] **AlternativeTo** -- List as an alternative to existing LLM benchmarking tools.
- [ ] **ToolsForHumans.ai** or similar AI tool directories -- Submit listing.

---

## Chinese-Language Platforms

The default catalog features Chinese cloud providers, so there is natural interest from the Chinese developer community.

### Developer Communities

- [ ] **V2EX** -- Post in the "Python" or "Developer" node. V2EX audience appreciates technical depth. Write in Chinese, link to the Chinese README and User Manual.
- [ ] **Juejin (掘金)** -- Publish a Chinese version of the blog post. Juejin is a major Chinese dev blog platform. Tags: `LLM`, `Python`, `开源`, `AI`.
- [ ] **SegmentFault** -- Cross-post the Chinese blog post. Similar audience to Stack Overflow in China.
- [ ] **CSDN** -- Cross-post. Largest Chinese developer community, good for SEO even if the community is less curated.

### Social Media

- [ ] **WeChat Official Account** -- If you have one, publish a Chinese article. WeChat articles get high engagement in the Chinese tech community.
- [ ] **Zhihu (知乎)** -- Post as an article or answer a relevant question (e.g., "How to choose the right LLM for production?"). Zhihu rewards in-depth technical content.
- [ ] **Weibo** -- Brief announcement linking to GitHub.
- [ ] **Xiaohongshu (小红书)** -- If targeting a broader audience. Short-form post with screenshots.

### Provider Communities

- [ ] **Alibaba Cloud / DashScope community forums** -- Post about the tool. Mention that it integrates with their Qwen models natively.
- [ ] **Zhipu AI community** -- Share that SkillEval includes GLM models, including the free glm-4.5-flash tier.
- [ ] **MiniMax developer channels** -- If they have community forums or Discord, share there.

---

## Timing Strategy

### Recommended Launch Sequence

**Day 0 (Preparation):**
- Finalize GitHub repo (description, topics, social preview, release)
- Prepare all platform accounts and drafts
- Schedule or draft posts in advance

**Day 1 (Primary Launch):**
- Morning (US time): Hacker News "Show HN" submission
- Morning (US time): Twitter thread
- Morning (US time): dev.to blog post
- Midday: LinkedIn post
- Afternoon: Reddit posts (stagger across subreddits by 1-2 hours)

**Day 2-3 (Chinese Launch):**
- Morning (China time): V2EX post
- Morning (China time): Juejin blog post
- Afternoon: Zhihu article
- Share in provider community forums

**Day 4-7 (Follow-up):**
- Product Hunt launch (pick a Tuesday or Wednesday)
- Cross-post to Medium, Hashnode, SegmentFault, CSDN
- Respond to all comments and feedback across platforms
- If a post gains traction, share it on other platforms ("SkillEval made the front page of HN" is valid LinkedIn content)

### Timing Notes

- **Avoid Mondays and Fridays** for primary launches. Engagement peaks Tuesday-Thursday.
- **Hacker News** is best submitted 8-10 AM US Eastern, Tuesday-Thursday.
- **Chinese platforms** are best posted 9-11 AM China Standard Time (CST), weekdays.
- **Product Hunt** launches reset at midnight PT. Submit just after midnight to maximize the 24-hour window, or submit in the morning and rely on organic votes.
- **Do not launch everything simultaneously.** Stagger across 1-2 days so you can respond to feedback on each platform.

---

## Cross-Promotion Between EN and ZH Communities

- [ ] English README links to Chinese README (`README_ZH.md`) and Chinese User Manual
- [ ] Chinese posts link to the English blog post for bilingual readers
- [ ] If a post does well on HN or Reddit, mention it in Chinese community posts as social proof
- [ ] If a post does well on V2EX or Juejin, mention it in English posts to highlight the China-origin provider support
- [ ] Consider a "Why Chinese LLM providers?" section in follow-up content -- the cost advantage (free tier, competitive pricing) is a genuine differentiator

---

## Post-Launch

- [ ] Monitor GitHub issues and stars for the first week
- [ ] Respond to every comment on every platform within 24 hours
- [ ] Track which platforms drive the most traffic (GitHub referrer stats)
- [ ] Collect feature requests and create GitHub issues
- [ ] Write a follow-up post if you hit a milestone (100 stars, interesting user stories, new providers added)
- [ ] Update the model catalog if providers change pricing
- [ ] Consider publishing benchmark results (e.g., "We tested 10 models on 5 common extraction tasks -- here are the results") as follow-up content
