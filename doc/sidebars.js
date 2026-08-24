// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/installation',
        'getting-started/quick-start',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/plugin-lifecycle',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/writing-plugins',
        'guides/api-injection',
        'guides/strategies',
        'guides/dependency-management',
        'guides/pyinstaller',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api/plugin-client',
        'api/plugin-manager',
        'api/worker',
        'api/installer',
      ],
    },
    'testing',
  ],
};

export default sidebars;
