import matplotlib as mpl
import matplotlib.pyplot as pylab
import numpy as np
import scipy.cluster.hierarchy as sch
import scipy.spatial.distance as dist
from scipy.stats import chisquare
from scipy.stats.mstats import kruskalwallis

# heatmap layout constants
WINDOW_HEIGHT = 30
WINDOW_WIDTH = 30
SPACING = 0.01  # spacing between plot elements
TRACK = 0.01  # height of individual track elements
FEATURE_W = 0.1  # width of left dendrogram (clustering of features)
FEATURE_X = SPACING  # horizontal offset for left dendrogram
FEATURE_Y = SPACING  # vertical offset for left dendrogram
HEATMAP_X = FEATURE_X + FEATURE_W + SPACING  # horizontal offset for heatmap
HEATMAP_Y = FEATURE_Y  # vertical offset for heatmap
HEATMAP_W = 1 - FEATURE_W - 3 * SPACING  # width of heatmap
SAMPLE_H = 0.1  # height of top dendrogram (clustering of samples)
SAMPLE_W = HEATMAP_W  # width of top dendrogram
SAMPLE_X = HEATMAP_X  # horizontal offset of top dendrogram
TRACK_W = HEATMAP_W  # width of tracks
TRACK_X = HEATMAP_X  # horizontal offset of tracks


def RiskCluster(Gradients, Raw, Symbols, N=30, Tau=0.05):
    """
    Generates a clustering and heatmap given risk profiles generated by
    Risk_Cohort. Analyzed features to identify and display cluster association
    mutations and copy number variations.

    Parameters
    ----------
    Gradients : array_like
    Numpy array containing feature/sample gradients obtained by Risk_Cohort.
    Features are in columns and samples are in rows.

    Raw : array_like
    Numpy array containing raw, unnormalized feature values. These are used to
    examine associations between feature values and cluster assignments.
    Features are in columns and samples are in rows.

    Symbols : array_like
    List containing strings describing features. See Notes below for
    restrictions on symbol names.

    N : scalar
    Number of features to include in clustering analysis. Features are scored
    by absolute mean gradient and the highest N magnitude features will be used
    in clustering. All features are used when examining cluster associations
    regardless of the value of N.

    Tau : scalar
    Threshold for statistical significance when examining cluster associations.

    Returns
    -------
    Figure : figure handle
        Handle to figure used for saving image to disk i.e.
        Figure.savefig('heatmap.pdf')

    SampleIndices : array_like
        Cluster labels for the risk-gradient clustering of input samples.

    Notes
    -----
    Suffixes like '_Mut' and '_CNV' that are generated by the package
    tcgaintegrator to identify feature types are required analysis.

    See Also
    --------
    RiskCohort
    """

    # calculate rank order of features
    Order = np.argsort(-np.abs(np.mean(Gradients, axis=0)))

    # copy data, re-order, normalize
    Normalized = Gradients[:, Order[0:N]].copy()
    Normalized = (Normalized - np.mean(Normalized, axis=0)) / \
        np.std(Normalized, axis=0)

    # transpose so that samples are in columns
    Normalized = Normalized.transpose()

    # generate figure
    Figure = pylab.figure(figsize=(WINDOW_WIDTH, WINDOW_HEIGHT))

    # cluster samples and generate dendrogram
    SampleDist = dist.pdist(Normalized.T, 'correlation')
    SampleDist = dist.squareform(SampleDist)
    SampleLinkage = sch.linkage(SampleDist, method='average',
                                metric='correlation')
    Labels = sch.fcluster(SampleLinkage, 0.7*max(SampleLinkage[:, 2]),
                          'distance')

    # cluster features and generate dendrogram
    FeatureDist = dist.pdist(Normalized, 'correlation')
    FeatureDist = dist.squareform(FeatureDist)
    FeatureLinkage = sch.linkage(FeatureDist, method='average',
                                 metric='correlation')

    # capture cluster associations
    Significant = ClusterAssociations(Raw, Symbols, Labels, Tau)

    # calculate layout parameters
    TRACK_H = TRACK * len(Significant)  # total height of tracks
    HEATMAP_H = 1 - SAMPLE_H - TRACK_H - 4 * SPACING
    TRACK_Y = HEATMAP_H + 2 * SPACING
    FEATURE_H = HEATMAP_H
    SAMPLE_Y = HEATMAP_H + TRACK_H + 3 * SPACING

    # layout and generate top dendrogram (samples)
    SampleHandle = Figure.add_axes([SAMPLE_X, SAMPLE_Y, SAMPLE_W, SAMPLE_H],
                                   frame_on=False)
    SampleDendrogram = sch.dendrogram(SampleLinkage)
    SampleHandle.set_xticks([])
    SampleHandle.set_yticks([])

    # define sample order
    SampleOrder = SampleDendrogram['leaves']

    # layout and generate left dendrogram (features)
    FeatureHandle = Figure.add_axes([FEATURE_X, FEATURE_Y,
                                     FEATURE_W, FEATURE_H],
                                    frame_on=False)
    FeatureDendrogram = sch.dendrogram(FeatureLinkage, orientation='right')
    FeatureHandle.set_xticks([])
    FeatureHandle.set_yticks([])

    # reorder input matrices based on clustering and capture order
    Reordered = Normalized[:, SampleDendrogram['leaves']]
    Reordered = Reordered[FeatureDendrogram['leaves'], :]

    # layout and generate heatmap
    Heatmap = Figure.add_axes([HEATMAP_X, HEATMAP_Y, HEATMAP_W, HEATMAP_H],
                              frame_on=False)
    Heatmap.matshow(Reordered, aspect='auto', origin='lower',
                    cmap=pylab.cm.bwr)
    Heatmap.set_xticks([])
    Heatmap.set_yticks([])

    # extract mutation values from raw features
    SigMut = [Symbol for Symbol in Significant if
              Symbol.strip()[-4:] == "_Mut"]
    Indices = [i for i, Symbol in enumerate(Symbols) if Symbol in set(SigMut)]
    Mutations = Raw[:, Indices]
    Mutations = Mutations[SampleOrder, :].T

    # extract CNV values from raw features
    SigCNV = [Symbol for Symbol in Significant if
              Symbol.strip()[-4:] == "_CNV"]
    Indices = [i for i, Symbol in enumerate(Symbols) if Symbol in set(SigCNV)]
    CNVs = Raw[:, Indices]
    CNVs = CNVs[SampleOrder, :].T

    # layout and generate mutation tracks
    gm = Figure.add_axes([TRACK_X, TRACK_Y + len(SigCNV)*TRACK,
                          TRACK_W, TRACK_H - len(SigCNV)*TRACK],
                         frame_on=False)
    cmap_g = mpl.colors.ListedColormap(['k', 'w'])
    gm.matshow(Mutations, aspect='auto', origin='lower', cmap=cmap_g)
    for i in range(len(SigMut)):
        gm.text(-SPACING, i / np.float(len(SigMut)) +
                1/np.float(2*len(SigMut)),
                SigMut[i], fontsize=6,
                verticalalignment='center',
                horizontalalignment='right',
                transform=gm.transAxes)
    gm.set_xticks([])
    gm.set_yticks([])

    # layout and generate CNV tracks
    cnv = Figure.add_axes([TRACK_X, TRACK_Y,
                           TRACK_W, TRACK_H - len(SigMut)*TRACK],
                          frame_on=False)
    cnv.matshow(CNVs, aspect='auto', origin='lower', cmap=pylab.cm.bwr)
    for i in range(len(SigCNV)):
        cnv.text(-SPACING, i / np.float(len(SigCNV)) +
                 1/np.float(2*len(SigCNV)),
                 SigCNV[i], fontsize=6,
                 verticalalignment='center',
                 horizontalalignment='right',
                 transform=cnv.transAxes)
    cnv.set_xticks([])
    cnv.set_yticks([])

    # return cluster labels
    return Figure, Labels


def ClusterAssociations(Raw, Symbols, Labels, Tau=0.05):
    """
    Examines associations between cluster assigments of samples and copy-number
    and mutation events.

    Parameters
    ----------
    Raw : array_like
    Numpy array containing raw, unnormalized feature values. These are used to
    examine associations between feature values and cluster assignments.
    Features are in columns and samples are in rows.

    Symbols : array_like
    List containing strings describing features. See Notes below for
    restrictions on symbol names.

    Labels : array_like
    Cluster labels for the samples in 'Raw'.

    Tau : scalar
    Threshold for statistical significance when examining cluster associations.

    Returns
    -------
    Significant : array_like
    List of copy number and mutation features from 'Raw' that are significantly
    associated with the clustering 'Labels'.



    Notes
    -----
    Suffixes like '_Mut' and '_CNV' that are generated by the package
    tcgaintegrator to identify feature types are required analysis.

    See Also
    --------
    RiskCohort, RiskCluster
    """

    # initialize list of symbols with significant associations
    Significant = []

    # get feature type from 'Symbols'
    Suffix = [Symbol[str.rfind(str(Symbol), '_')+1:] for Symbol in Symbols]

    # identify mutations and CNVs
    Mutations = [index for index, x in enumerate(Suffix) if x == "Mut"]
    CNVs = [index for index, x in enumerate(Suffix) if x == "CNV"]

    # test mutation associations
    for i in np.arange(len(Mutations)):

        # build contingency table - expected and observed
        Observed = np.zeros((2, np.max(Labels)))
        for j in np.arange(1, np.max(Labels)+1):
            Observed[0, j-1] = np.sum(Raw[Labels == j, Mutations[i]] == 0)
            Observed[1, j-1] = np.sum(Raw[Labels == j, Mutations[i]] == 1)
        RowSum = np.sum(Observed, axis=0)
        ColSum = np.sum(Observed, axis=1)
        Expected = np.outer(ColSum, RowSum) / np.sum(Observed.flatten())

        # perform test
        stat, p = chisquare(Observed, Expected, ddof=1, axis=None)
        if p < Tau:
            Significant.append(Symbols[Mutations[i]])

    # copy number associations
    for i in np.arange(len(CNVs)):

        # separate out CNV values by cluster and perform test
        if(np.max(Labels) == 2):
            CNV1 = Raw[Labels == 1, CNVs[i]]
            CNV2 = Raw[Labels == 2, CNVs[i]]
            stat, p = kruskalwallis(CNV1, CNV2)
        elif(np.max(Labels) == 3):
            CNV1 = Raw[Labels == 1, CNVs[i]]
            CNV2 = Raw[Labels == 2, CNVs[i]]
            CNV3 = Raw[Labels == 3, CNVs[i]]
            stat, p = kruskalwallis(CNV1, CNV2, CNV3)
        elif(np.max(Labels) == 4):
            CNV1 = Raw[Labels == 1, CNVs[i]]
            CNV2 = Raw[Labels == 2, CNVs[i]]
            CNV3 = Raw[Labels == 3, CNVs[i]]
            CNV4 = Raw[Labels == 4, CNVs[i]]
            stat, p = kruskalwallis(CNV1, CNV2, CNV3, CNV4)
        elif(np.max(Labels) == 5):
            CNV1 = Raw[Labels == 1, CNVs[i]]
            CNV2 = Raw[Labels == 2, CNVs[i]]
            CNV3 = Raw[Labels == 3, CNVs[i]]
            CNV4 = Raw[Labels == 4, CNVs[i]]
            CNV5 = Raw[Labels == 5, CNVs[i]]
            stat, p = kruskalwallis(CNV1, CNV2, CNV3, CNV4, CNV5)
        if p < Tau:
            Significant.append(Symbols[CNVs[i]])

    # return names of features with significant associations
    return Significant