"""Hand-curated domain taxonomy. Notes listed here keep this domain;
unlisted notes get their domain from the LLM tagger (meta/tags.json)."""

FINE_TAXONOMY = {
    "Real Analysis (Foundations & Sequences)": [
        "axiom-of-completeness.ipynb", "real-numbers.ipynb", "supremum-infimum.ipynb", "archimedean-property-of-R.ipynb",
        "def-dedekind-cuts.ipynb", "prop-dedekind-cuts.ipynb", "density-theorem-of-R.ipynb", "existence-of-decimal-expansion-in-R.ipynb",
        "existence-of-nth-roots-in-R.ipynb", "zero-squeeze-in-R.ipynb", "adding-inequalities.ipynb", "triangle-inequality.ipynb",
        "absolute-value.ipynb", "arithmetic-geometric-mean-inequality.ipynb", "ordered-field.ipynb", "ordered-set.ipynb", "order.ipynb", "field.ipynb",
        "pre-set-theory.ipynb", "pre-logic.ipynb", "cardinality.ipynb", "interval.ipynb", "sequence.ipynb", "sequence-limit.ipynb", "subsequences.ipynb",
        "geometric-sequence.ipynb", "composite-sequences-limit.ipynb", "squeeze-theorem-for-sequences.ipynb", "limsup-liminf.ipynb",
        "Cauchy-sequences.ipynb", "Bolzano-Weierstrass-theorem.ipynb", "nested-interval-property.ipynb", "cantor-set.ipynb"
    ],
    "Measure Theory & Integration": [
        "Lebesgue-measure.ipynb", "lebesgue-outer-measure.ipynb", "lebesgue-integral.ipynb", "Borel-sets-and-measurability.ipynb",
        "measurable-functions.ipynb", "measurable-sets.ipynb", "measurable-sets-algebra.ipynb", "measure.ipynb", "measure-properties-and-completion.ipynb",
        "limits-of-measurable-functions.ipynb", "fatous-lemma-and-convergence-theorems.ipynb", "continuity-of-measure.ipynb",
        "sigma-algebra.ipynb", "sigma-algebra-of-measurable-sets.ipynb"
    ],
    "Metric Spaces & Topology": [
        "metric-spaces.ipynb", "metric-space-topology.ipynb", "compactness.ipynb", "nests-of-compacts.ipynb", "continuity-and-compactness.ipynb",
        "homeomorphisms-compactness.ipynb", "relative-topology-inheritance.ipynb", "continuity-topology.ipynb", "function-continuity.ipynb",
        "uniform-continuity.ipynb", "sequences-metric-spaces.ipynb", "contractions.ipynb", "product-metrics-continuity.ipynb",
        "normed-vector-spaces.ipynb", "func-lim-seq-lim.ipynb", "limit.ipynb", "real-valued-functions.ipynb", "def-functions-mappings.ipynb", "completeness.ipynb"
    ],
    "Function Spaces & Fixed Points": [
        "function-spaces.ipynb", "banach-fp-thm.ipynb", "brouwer-fixed-point-theorem.ipynb", "equicontinuity-Arzela-Ascoli-Thm.ipynb",
        "ode-and-picards-thm.ipynb"
    ],
    "Probability Foundations & Combinatorics": [
        "probability.ipynb", "probability-naive-definition.ipynb", "probability-properties.ipynb", "sample-space.ipynb", "event.ipynb", "outcome.ipynb",
        "experiment.ipynb", "conditional-probability.ipynb", "law-of-total-probability.ipynb", "independence-of-events.ipynb", "inclusion-exclusion.ipynb",
        "adjusting-for-overcounting.ipynb", "sampling-with-replacement.ipynb", "sampling-without-replacement.ipynb", "multiplication-rule.ipynb",
        "binomial-coefficient.ipynb", "binomial-coefficient-formula.ipynb", "binomial-theorem.ipynb", "vandermonde’s-identity.ipynb", "story-proofs.ipynb",
        "partnerships.ipynb", "full-house.ipynb", "birthday-problem.ipynb", "monty-hall-problem.ipynb", "simpsons-paradox.ipynb", "newton-pepys-problem.ipynb",
        "de-montmorts-matching-problem.ipynb", "bose-einstein-problem.ipynb", "occupancy-problem.ipynb", "coupon-collector-problem.ipynb"
    ],
    "Random Variables & Distributions": [
        "random-variables.ipynb", "indicator-rv.ipynb", "probability-mass-function.ipynb", "cumulative-distribution-functions.ipynb",
        "bernoulli-and-binomial-distributions.ipynb", "hypergeometric-distribution.ipynb", "binomial-hypergeometric-connections.ipynb",
        "geometric-and-negative-binomial-dist.ipynb", "poisson-distribution.ipynb", "multinomial-distribution.ipynb", "expectation.ipynb",
        "expectations-of-discrete-distributions.ipynb", "variance.ipynb", "covariance-and-correlation.ipynb", "lotus.ipynb",
        "conditional-expectation.ipynb", "moment-generating-functions.ipynb", "joint-distribution.ipynb", "independence-of-rvs.ipynb",
        "functions-of-random-variables.ipynb", "transformations-and-convolutions.ipynb", "probability-density-function.ipynb",
        "uniform-distribution.ipynb", "exponential-distribution.ipynb", "gamma-function-and-distribution.ipynb", "beta-distribution.ipynb",
        "normal-distribution.ipynb", "multivariate-normal-distribution.ipynb", "Cauchy-distribution.ipynb", "student-t-distribution.ipynb",
        "chi-square-distribution.ipynb", "order-statistics.ipynb"
    ],
    "Inequalities & Limit Theorems": [
        "markovs-inequality.ipynb", "chebyshevs-inequality.ipynb", "jensens-inequality.ipynb", "Cauchy-Schwarz-inequality.ipynb",
        "law-of-large-numbers-and-central-limit-theorem.ipynb", "borel-cantelli-lemma.ipynb", "probabilistic-for-existence-proof.ipynb"
    ],
    "Stochastic Processes": [
        "stochastic-processes-foundations.ipynb", "gamblers-ruin.ipynb", "branching-process.ipynb", "brownian-motion.ipynb", "gaussian-processes.ipynb"
    ],
    "Mathematical Finance & Portfolio Theory": [
        "stochastic-models-in-finance.ipynb", "single-period-investment-model.ipynb", "markowitz-portfolio-theory-2-assets.ipynb",
        "risk-measures.ipynb", "cs-mab-signal-selection.ipynb", "cs-emh-btc-ma-model.ipynb"
    ],
    "Time Series Analysis": [
        "time-series-returns.ipynb", "autocorrelation-and-stationarity.ipynb", "autoregressive-models.ipynb", "moving-average-models.ipynb",
        "arma-models.ipynb", "arch-and-garch-models.ipynb", "vector-autoregressive-models.ipynb", "vector-moving-average.ipynb",
        "augmented-dickey-fuller-test.ipynb", "cointegration.ipynb", "multivariate-time-series.ipynb"
    ],
    "Difference Equations & Dynamics": [
        "intro-to-difference-equations.ipynb", "first-order-linear-difference-equations-and-equilibriums.ipynb",
        "second-order-linear-difference-equations.ipynb"
    ],
    "Optimization & Linear Programming": [
        "linear-programs.ipynb", "polyhedra-and-polytopes.ipynb", "convex-sets-and-convex-hulls.ipynb", "hyperplane-separation-theorems.ipynb",
        "lagrangian-and-kkt-conditions.ipynb"
    ],
    "Statistical Inference & Estimation": [
        "maximum-likelihood-estimation.ipynb", "statistical-inference.ipynb"
    ]
}
