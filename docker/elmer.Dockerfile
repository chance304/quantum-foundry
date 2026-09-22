# Elmer FEM (thermo-mechanical coupling), built from source.
#
# NOT YET BUILT/TESTED — this reflects a standard ElmerCSC/elmerfem source build
# recipe as of this session's knowledge, not a verified working image. Verify and
# fix as needed before thermal/elmer_backend.py depends on it — see docs/ROADMAP.md.
#
# Rationale for a dedicated container instead of conda: see docs/DECISIONS.md
# "Elmer runs via a single dedicated Docker container, not conda".

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        gfortran \
        libblas-dev \
        liblapack-dev \
        libopenmpi-dev \
        openmpi-bin \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
# Pinned to a specific commit of the default branch ("devel"), not the
# mutable branch head -- same supply-chain rationale as SHA-pinning
# third-party GitHub Actions in ci.yml: an upstream change/force-push
# shouldn't be able to silently alter what gets built into this image.
# Re-verify and bump deliberately when Elmer needs to be updated.
# (2026-08-04 security/supply-chain audit)
ARG ELMERFEM_COMMIT=341a71620d2fe67bb63ec7e17ab6c0215e2f503a
RUN git clone https://github.com/ElmerCSC/elmerfem.git \
    && git -C elmerfem checkout "${ELMERFEM_COMMIT}"

WORKDIR /opt/elmerfem/build
RUN cmake .. \
        -DCMAKE_INSTALL_PREFIX=/opt/elmer \
        -DWITH_MPI=TRUE \
        -DWITH_ELMERGUI=FALSE \
    && make -j"$(nproc)" \
    && make install

ENV PATH="/opt/elmer/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/elmer/lib:${LD_LIBRARY_PATH}"

WORKDIR /work
ENTRYPOINT ["/opt/elmer/bin/ElmerSolver"]
