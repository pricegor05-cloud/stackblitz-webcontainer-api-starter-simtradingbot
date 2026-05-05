# =========================
# 🧬 STEP 3 — CONTROLLED EVOLUTION ENGINE (FIXED)
# =========================

MAX_AGENTS = 10


def evolve_agents():
    global agents, learn, evolver

    new_agents = []
    updated_scores = learn.agent_score.copy()

    for name, agent in agents:
        score = learn.agent_score.get(name, 1.0)

        # 🟢 strong performers survive unchanged
        if score > 1.2:
            new_agents.append((name, agent))

        # 🔴 weak performers removed
        elif score < 0.8:
            continue

        # 🧬 medium performers mutate
        else:
            mutated = evolver.mutate(agent)
            new_name = name + "_v2"

            new_agents.append((new_name, mutated))

            # inherit score with controlled noise
            updated_scores[new_name] = score * random.uniform(0.9, 1.1)

    # 🧠 cap system size (prevents AI explosion)
    new_agents = sorted(
        new_agents,
        key=lambda x: learn.agent_score.get(x[0], 1.0),
        reverse=True
    )[:MAX_AGENTS]

    # 🧠 remove orphan scores (cleanup)
    clean_scores = {}
    for name, _ in new_agents:
        clean_scores[name] = updated_scores.get(name, 1.0)

    learn.agent_score = clean_scores

    return new_agents