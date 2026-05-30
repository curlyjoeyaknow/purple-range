# Run guide (properly pinned)

Stand up the victim at the pinned Vulhub commit:

```bash
git clone https://github.com/vulhub/vulhub.git
git checkout d277a8693e588684e951dddb0733809e53881a3c
docker compose up -d
```

And use the pinned image:

```yaml
image: nginx:1.27.3
```

Nothing in this guide is unpinned — the gate MUST NOT flag any line here.
