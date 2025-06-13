#!/usr/bin/env Rscript

install_CytoTRACE <- function (url) {
    cytotrace <- basename(url)
    if (!file.exists(cytotrace))
    download.file(url, cytotrace)
    
    if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
    
    if (!requireNamespace("sva", quietly = TRUE))
    BiocManager::install("sva")
    
    if (!requireNamespace("remotes", quietly = TRUE))
    install.packages("remotes")
    
    remotes::install_local(cytotrace)
}

# Install CytoTRACE if not available
if (!requireNamespace("CytoTRACE", quietly = TRUE)) {
    url = "https://cytotrace.stanford.edu/CytoTRACE_0.3.3.tar.gz"
    install_CytoTRACE(url=url)
}