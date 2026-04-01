declare module "d3-sankey" {
  export type SankeyNodeMinimal<N, L> = N & {
    x0: number;
    x1: number;
    y0: number;
    y1: number;
    value: number;
    sourceLinks: SankeyLinkMinimal<N, L>[];
    targetLinks: SankeyLinkMinimal<N, L>[];
  };

  export type SankeyLinkMinimal<N, L> = L & {
    width: number;
    y0: number;
    y1: number;
    source: SankeyNodeMinimal<N, L>;
    target: SankeyNodeMinimal<N, L>;
  };

  export interface SankeyGraph<N, L> {
    nodes: SankeyNodeMinimal<N, L>[];
    links: SankeyLinkMinimal<N, L>[];
  }

  export interface SankeyLayout<N, L> {
    (graph: { nodes: N[]; links: L[] }): SankeyGraph<N, L>;
    nodeId(accessor: (node: N) => string): SankeyLayout<N, L>;
    nodeAlign(accessor: (node: N, totalColumns: number) => number): SankeyLayout<N, L>;
    nodeSort(compare: ((a: N, b: N) => number) | null): SankeyLayout<N, L>;
    linkSort(compare: ((a: L, b: L) => number) | null): SankeyLayout<N, L>;
    nodeWidth(width: number): SankeyLayout<N, L>;
    nodePadding(padding: number): SankeyLayout<N, L>;
    extent(extent: [[number, number], [number, number]]): SankeyLayout<N, L>;
  }

  export function sankey<N, L>(): SankeyLayout<N, L>;
  export function sankeyLinkHorizontal<N, L>(): (
    link: SankeyLinkMinimal<N, L>
  ) => string | null;
}
