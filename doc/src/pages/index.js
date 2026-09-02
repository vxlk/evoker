import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';
import styles from './index.module.css';

function HeroSection() {
  return (
    <header className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.heroText}>
          <Heading as="h1" className={styles.heroTitle}>
            Evoker
          </Heading>
          <p className={styles.heroTagline}>
            A dead-simple plugin system for Python desktop apps.
          </p>
          <p className={styles.heroSubtext}>
            Ship your application with <strong>fully decoupled plugins</strong> that run in isolated processes.
            Users extend your app by dropping a folder in — no internet required, no install wizards, no shared state bugs.
          </p>
          <div className={styles.heroButtons}>
            <Link className={styles.btnPrimary} to="/docs/intro">
              Get Started →
            </Link>
            <Link className={styles.btnSecondary} to="https://github.com/vxlk/Evoker">
              GitHub
            </Link>
          </div>
        </div>
        <div className={styles.heroDiagram}>
          <div className={styles.diagramContainer}>
            <div className={styles.hostBox}>
              <span className={styles.boxLabel}>🖥️ Your App</span>
              <div className={styles.hostInner}>host.py</div>
            </div>
            <div className={styles.arrows}>
              <div className={styles.arrow}>→ XML-RPC →</div>
              <div className={styles.arrow}>→ XML-RPC →</div>
            </div>
            <div className={styles.pluginColumn}>
              <div className={styles.pluginBox}>
                <span className={styles.boxLabel}>🧩 Plugin A</span>
                <div className={styles.pluginInner}>Isolated Process</div>
              </div>
              <div className={styles.pluginBox}>
                <span className={styles.boxLabel}>🧩 Plugin B</span>
                <div className={styles.pluginInner}>Isolated Process</div>
              </div>
            </div>
          </div>
          <p className={styles.diagramCaption}>Plugins crash? Your app doesn't.</p>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    emoji: '📦',
    title: 'Drop-In Plugins',
    description: 'A plugin is just a folder with a manifest.json and __init__.py. Drop it into the plugins directory — done. No pip install, no compilation, no registration.',
  },
  {
    emoji: '🛡️',
    title: 'Crash Isolation',
    description: 'Every plugin runs in its own subprocess. A segfault, infinite loop, or bad import in a plugin never touches your host application.',
  },
  {
    emoji: '✈️',
    title: 'Air-Gapped Ready',
    description: 'Ship plugins with pre-built wheel files. Evoker installs dependencies from local wheels — no internet connection needed. Perfect for enterprise and offline deployments.',
  },
  {
    emoji: '💉',
    title: 'Inject Your APIs',
    description: 'Pass your own modules and libraries into plugin processes. Plugins import your host SDK as if it were a regular package — no duplication, no version conflicts.',
  },
  {
    emoji: '🔍',
    title: 'Deep Introspection',
    description: 'Plugin functions are inspected at load time — parameter names, types, defaults, and required flags are extracted automatically. Your host always knows exactly what a plugin expects.',
  },
  {
    emoji: '📦',
    title: 'Ships as an .exe',
    description: 'First-class PyInstaller support with custom hooks. Compile your entire app into a standalone binary. Users add plugins next to the .exe.',
  },
  {
    emoji: '⚡',
    title: 'Stateless Entrypoints',
    description: 'Designed for a host-driven, request-response model. Plugins act as stateless functions to invoke, enforcing clean API separation rather than chatty, two-way synchronized state.',
  },
];

function FeatureCard({emoji, title, description}) {
  return (
    <div className={styles.featureCard}>
      <div className={styles.featureEmoji}>{emoji}</div>
      <Heading as="h3" className={styles.featureTitle}>{title}</Heading>
      <p className={styles.featureDesc}>{description}</p>
    </div>
  );
}

function FeaturesSection() {
  return (
    <section className={styles.features}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          Why Evoker?
        </Heading>
        <div className={styles.featureGrid}>
          {features.map((props, idx) => (
            <FeatureCard key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorksSection() {
  return (
    <section className={styles.howItWorks}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          How It Works
        </Heading>
        <div className={styles.steps}>
          <div className={styles.step}>
            <div className={styles.stepNumber}>1</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Write a plugin</Heading>
              <CodeBlock language="python" title="plugins/hello/__init__.py">
{`def greet(name: str) -> str:
    return f"Hello, {name}!"`}
              </CodeBlock>
            </div>
          </div>
          <div className={styles.step}>
            <div className={styles.stepNumber}>2</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Call it from your app</Heading>
              <CodeBlock language="python" title="host.py">
{`from evoker_client.client import PluginClient

client = PluginClient(Path("plugins"))
client.start_worker()
result = client.run_action("hello", "greet",
                           {"name": "World"})`}
              </CodeBlock>
            </div>
          </div>
          <div className={styles.step}>
            <div className={styles.stepNumber}>3</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Ship it</Heading>
              <p className={styles.stepText}>
                Compile with PyInstaller. Users drop new plugin folders next to the <code>.exe</code>.
                No Python installed. No internet needed. It just works.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className={styles.cta}>
      <div className="container">
        <Heading as="h2" className={styles.ctaTitle}>
          Ready to build something unstoppable?
        </Heading>
        <div className={styles.heroButtons}>
          <Link className={styles.btnPrimary} to="/docs/getting-started/installation">
            Install Evoker →
          </Link>
          <Link className={styles.btnSecondary} to="https://github.com/vxlk/evoker-example">
            See Full Example
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <Layout
      title="Evoker — Plugin System for Python Desktop Apps"
      description="A dead-simple, process-isolated plugin system for Python desktop applications. Ship extensible apps with air-gapped plugin support.">
      <HeroSection />
      <main>
        <FeaturesSection />
        <HowItWorksSection />
        <CTASection />
      </main>
    </Layout>
  );
}
